package app.linuxpad.runtime

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RegistryTest {
    // shape of the real debian:trixie-slim index: several platforms and attestation entries
    private val index = JSONObject("""{"manifests":[
      {"digest":"sha256:amd","platform":{"architecture":"amd64","os":"linux"}},
      {"digest":"sha256:att","platform":{"architecture":"unknown","os":"unknown"}},
      {"digest":"sha256:arm","platform":{"architecture":"arm64","os":"linux","variant":"v8"}}]}""")

    @Test fun picksTheArm64Image() = assertEquals("sha256:arm", Registry.pickArm64(index))

    @Test fun noArm64GivesNull() = assertNull(Registry.pickArm64(JSONObject("""{"manifests":[{"digest":"x","platform":{"architecture":"amd64","os":"linux"}}]}""")))

    @Test fun readsLayers() {
        val m = JSONObject("""{"layers":[{"mediaType":"application/vnd.oci.image.layer.v1.tar+gzip","size":30214037,"digest":"sha256:acd4"}]}""")
        val l = Registry.layersOf(m).single()
        assertEquals("sha256:acd4", l.digest); assertEquals(30214037L, l.size)
    }
}
