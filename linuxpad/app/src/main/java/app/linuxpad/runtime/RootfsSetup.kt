package app.linuxpad.runtime

import android.system.Os
import java.io.File

/** First-run fixes a root filesystem needs to work under PRoot on Android. */
object RootfsSetup {
    fun configure(root: File) {
        File(root, "etc").mkdirs()
        File(root, "etc/resolv.conf").delete()
        File(root, "etc/resolv.conf").writeText("nameserver 1.1.1.1\nnameserver 8.8.8.8\n")   // Android has no /etc/resolv.conf
        File(root, "etc/hosts").writeText("127.0.0.1 localhost\n::1 localhost ip6-localhost\n")
        // apt drops privileges to a user it cannot switch to under PRoot, so let it stay as (fake) root
        File(root, "etc/apt/apt.conf.d").mkdirs()
        File(root, "etc/apt/apt.conf.d/99linuxpad").writeText("APT::Sandbox::User \"root\";\n")
        listOf("tmp", "var/tmp").forEach { File(root, it).mkdirs(); Os.chmod(File(root, it).path, 0x3FF) } // 1777
        File(root, "root").mkdirs()
        listOf("proc", "sys", "dev", "run").forEach { File(root, it).mkdirs() }
    }
}
