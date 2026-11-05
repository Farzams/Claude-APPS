package app.linuxpad.runtime

import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.DigestInputStream
import java.security.MessageDigest

/**
 * Downloads a Linux image from a Docker/OCI registry (Docker Hub, anonymous pull).
 * Every blob is addressed by its SHA-256, so what we download is verified byte for byte,
 * and "debian:trixie-slim" always resolves to the newest security-patched image.
 */
object Registry {
    data class Layer(val digest: String, val size: Long, val mediaType: String)
    data class Progress(val phase: String, val done: Long = 0, val total: Long = 0)

    private const val AUTH = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:%s:pull"
    private const val HOST = "https://registry-1.docker.io/v2"
    private const val ACCEPT = "application/vnd.oci.image.index.v1+json," +
        "application/vnd.docker.distribution.manifest.list.v2+json," +
        "application/vnd.oci.image.manifest.v1+json," +
        "application/vnd.docker.distribution.manifest.v2+json"

    /** The digest of the linux/arm64 entry of an image index, or null when the index has none. */
    fun pickArm64(index: JSONObject): String? {
        val list = index.optJSONArray("manifests") ?: return null
        for (i in 0 until list.length()) {
            val m = list.getJSONObject(i)
            val p = m.optJSONObject("platform") ?: continue
            if (p.optString("os") == "linux" && p.optString("architecture") == "arm64") return m.getString("digest")
        }
        return null
    }

    fun layersOf(manifest: JSONObject): List<Layer> {
        val a = manifest.getJSONArray("layers")
        return (0 until a.length()).map { val l = a.getJSONObject(it); Layer(l.getString("digest"), l.optLong("size"), l.optString("mediaType")) }
    }

    private fun open(url: String, headers: Map<String, String>, depth: Int = 0): HttpURLConnection {
        val c = (URL(url).openConnection() as HttpURLConnection).apply {
            instanceFollowRedirects = false
            connectTimeout = 20_000
            readTimeout = 45_000
            headers.forEach { (k, v) -> setRequestProperty(k, v) }
        }
        val code = c.responseCode
        if (code in 300..399) {
            val loc = c.getHeaderField("Location") ?: error("redirect without a Location header")
            c.disconnect()
            require(depth < 5) { "too many redirects" }
            val next = URL(URL(url), loc)
            // The CDN uses a signed URL: sending our registry token there would be refused (and leaks it)
            val h = if (next.host == URL(url).host) headers else headers - "Authorization"
            return open(next.toString(), h, depth + 1)
        }
        if (code !in 200..299) { c.disconnect(); error("HTTP $code from ${URL(url).host}") }
        return c
    }

    private fun text(url: String, headers: Map<String, String>): String {
        val c = open(url, headers)
        return try { c.inputStream.bufferedReader().readText() } finally { c.disconnect() }
    }

    /** Downloads and unpacks [image]:[tag] (linux/arm64) into [dest]. Throws on any verification failure. */
    fun install(repo: String, tag: String, dest: File, work: File, onProgress: (Progress) -> Unit) {
        onProgress(Progress("Connecting to Docker Hub"))
        val token = JSONObject(text(AUTH.format("library/$repo"), emptyMap())).getString("token")
        val auth = mapOf("Authorization" to "Bearer $token", "Accept" to ACCEPT)

        onProgress(Progress("Finding the arm64 image"))
        val top = JSONObject(text("$HOST/library/$repo/manifests/$tag", auth))
        val manifest = if (top.has("manifests")) {
            val d = pickArm64(top) ?: error("no linux/arm64 image for $repo:$tag")
            JSONObject(text("$HOST/library/$repo/manifests/$d", auth))
        } else top
        val layers = layersOf(manifest)
        require(layers.isNotEmpty()) { "image has no layers" }

        val partial = File(dest.parentFile, dest.name + ".partial")
        partial.deleteRecursively(); partial.mkdirs()
        work.mkdirs()
        layers.forEachIndexed { i, layer ->
            val blob = File(work, "layer$i.tar.gz")
            download("$HOST/library/$repo/blobs/${layer.digest}", auth, blob, layer, "Downloading ${i + 1}/${layers.size}", onProgress)
            TarExtractor.extractTarGz(blob, partial) { n -> onProgress(Progress("Unpacking ${i + 1}/${layers.size}: $n files")) }
            blob.delete()
        }
        onProgress(Progress("Configuring"))
        RootfsSetup.configure(partial)
        dest.deleteRecursively()
        check(partial.renameTo(dest)) { "could not move the finished system into place" }
        onProgress(Progress("Done"))
    }

    private fun download(url: String, headers: Map<String, String>, out: File, layer: Layer, phase: String, onProgress: (Progress) -> Unit) {
        val md = MessageDigest.getInstance("SHA-256")
        val c = open(url, headers)
        try {
            val total = if (layer.size > 0) layer.size else c.contentLengthLong
            DigestInputStream(c.inputStream, md).use { input ->
                out.outputStream().buffered(1 shl 16).use { o ->
                    val buf = ByteArray(1 shl 16); var done = 0L; var last = 0L
                    while (true) {
                        val n = input.read(buf); if (n < 0) break
                        o.write(buf, 0, n); done += n
                        if (done - last >= 262_144) { last = done; onProgress(Progress(phase, done, total)) }
                    }
                    onProgress(Progress(phase, done, total))
                }
            }
        } finally { c.disconnect() }
        val got = "sha256:" + md.digest().joinToString("") { "%02x".format(it) }
        check(got == layer.digest) { "download is corrupt: expected ${layer.digest}, got $got" }
    }
}
