package app.pdftoolkit.mobile

import android.annotation.SuppressLint
import android.content.Context
import android.util.Base64
import android.util.Log
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.FileNotFoundException

data class ProjFile(val path: String, val bytes: ByteArray)
data class CompileResult(val ok: Boolean, val exit: Int, val log: String, val pdf: ByteArray?)

/**
 * Offline TeX: a hidden WebView runs BusyTeX (XeTeX/pdfTeX compiled to WebAssembly) from the app's own assets.
 * Nothing is downloaded and nothing leaves the phone.
 */
object TexEngine {
    private const val HOST = "appassets.androidplatform.net"
    private val TEXT_EXT = setOf("tex", "sty", "cls", "bib", "bst", "txt", "def", "cfg", "clo", "fd", "bbx", "cbx", "lbx", "dbx", "ltx", "md", "csv", "dat")

    private var webView: WebView? = null
    private var appCtx: Context? = null
    private val ready = CompletableDeferred<Unit>()
    private var pending: CompletableDeferred<CompileResult>? = null
    @Volatile private var lastPdf: ByteArray? = null

    private val _status = MutableStateFlow("")
    val status: StateFlow<String> = _status
    val logs = MutableSharedFlow<String>(extraBufferCapacity = 512)

    @SuppressLint("SetJavaScriptEnabled")
    fun attach(ctx: Context, root: ViewGroup) {
        appCtx = ctx.applicationContext
        if (webView == null) {
            val wv = WebView(ctx.applicationContext)
            wv.settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                allowFileAccess = false
                allowContentAccess = false
                cacheMode = WebSettings.LOAD_NO_CACHE
            }
            wv.webViewClient = object : WebViewClient() {
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? =
                    assetResponse(request)

                override fun onRenderProcessGone(view: WebView, detail: android.webkit.RenderProcessGoneDetail): Boolean {
                    Log.e("PDFTK", "WebView render process gone, crashed=${detail.didCrash()}")
                    _status.value = "engine-crashed"
                    pending?.complete(CompileResult(false, -1, "The TeX engine stopped (not enough memory?).", null))
                    pending = null
                    return true
                }
            }
            wv.addJavascriptInterface(Bridge(), "Android")
            wv.loadUrl("https://$HOST/assets/tex/tex_host.html")
            webView = wv
        }
        (webView!!.parent as? ViewGroup)?.removeView(webView)
        root.addView(webView, ViewGroup.LayoutParams(1, 1))
    }

    private fun mimeOf(path: String): String = when (path.substringAfterLast('.', "").lowercase()) {
        "html" -> "text/html"
        "js" -> "application/javascript"
        "wasm" -> "application/wasm"
        "json" -> "application/json"
        else -> "application/octet-stream"
    }

    private fun assetResponse(req: WebResourceRequest): WebResourceResponse? {
        val uri = req.url
        if (uri.host != HOST) return null
        val path = uri.path ?: return null
        if (!path.startsWith("/assets/")) return null
        val name = path.removePrefix("/assets/")
        val headers = mapOf("Access-Control-Allow-Origin" to "*", "Cache-Control" to "no-store")
        return try {
            val stream = appCtx!!.assets.open(name)
            WebResourceResponse(mimeOf(name), if (name.endsWith(".html") || name.endsWith(".js") || name.endsWith(".json")) "utf-8" else null, 200, "OK", headers, stream)
        } catch (e: FileNotFoundException) {
            WebResourceResponse("text/plain", "utf-8", 404, "Not Found", headers, "".byteInputStream())
        }
    }

    private class Bridge {
        @JavascriptInterface fun onReady() { ready.complete(Unit); _status.value = "ready" }
        @JavascriptInterface fun onLog(s: String) { logs.tryEmit(s); Log.i("PDFTK", "tex: " + s.take(300)) }
        @JavascriptInterface fun onStatus(s: String) { _status.value = s; Log.i("PDFTK", "engine status: $s") }
        @JavascriptInterface fun onPdf(b64: String) { lastPdf = Base64.decode(b64, Base64.DEFAULT) }
        @JavascriptInterface fun onDone(json: String) {
            val o = JSONObject(json)
            val d = pending
            pending = null
            d?.complete(CompileResult(o.optBoolean("ok"), o.optInt("exit", -1), o.optString("log"), if (o.optBoolean("ok")) lastPdf else null))
        }
    }

    suspend fun compile(files: List<ProjFile>, main: String, driver: String = "xetex_bibtex8_dvipdfmx"): CompileResult {
        ready.await()
        return withContext(Dispatchers.Main) {
            val wv = webView ?: return@withContext CompileResult(false, -1, "The TeX engine is not available.", null)
            if (pending != null) return@withContext CompileResult(false, -1, "A compilation is already running.", null)
            val done = CompletableDeferred<CompileResult>()
            pending = done
            lastPdf = null
            val arr = JSONArray()
            for (f in files) {
                val o = JSONObject().put("path", f.path)
                val ext = f.path.substringAfterLast('.', "").lowercase()
                if (ext in TEXT_EXT) o.put("text", String(f.bytes, Charsets.UTF_8))
                else o.put("b64", Base64.encodeToString(f.bytes, Base64.NO_WRAP))
                arr.put(o)
            }
            val req = JSONObject().put("main", main).put("driver", driver).put("files", arr)
            wv.evaluateJavascript("compileProject(" + JSONObject.quote(req.toString()) + ")", null)
            done.await()
        }
    }
}
