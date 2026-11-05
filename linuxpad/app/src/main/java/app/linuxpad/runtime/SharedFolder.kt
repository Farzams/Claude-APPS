package app.linuxpad.runtime

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Environment
import android.provider.Settings
import android.system.Os
import java.io.File
import java.nio.file.Files

/**
 * One folder that both Android and Linux see: "LinuxShared" in the tablet's internal storage, shown in Linux as /root/Shared
 * and as the icon "Shared" on the desktop. Linux sees nothing else of the tablet's storage.
 * Android 11 and newer need the "All files access" permission for an app to create a folder there.
 */
object SharedFolder {
    const val NAME = "LinuxShared"
    const val GUEST_PATH = "/root/Shared"

    fun hostDir() = File(Environment.getExternalStorageDirectory(), NAME)

    fun hasAccess() = Environment.isExternalStorageManager()

    /** The system screen where the user allows the access. */
    fun accessIntent(ctx: Context) = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:${ctx.packageName}"))

    /** Creates the folder, the mount point and the desktop icon; returns the proot bind (host to guest), or null while access is missing. */
    fun prepare(root: File): Pair<String, String>? {
        if (!hasAccess()) return null
        val host = hostDir()
        if (!host.isDirectory && !host.mkdirs()) return null
        File(host, "README.txt").takeIf { !it.exists() }?.writeText(
            "This folder is shared between Android and the Linux system of LinuxPad.\n" +
                "On Android: internal storage, folder $NAME.\nIn Linux: the icon \"Shared\" on the desktop, or $GUEST_PATH.\n" +
                "Keep projects with git, symlinks or permissions inside the Linux home folder instead; this folder has no Linux permissions.\n")
        File(root, "root/Shared").mkdirs()
        val desktop = File(root, "root/Desktop").apply { mkdirs() }
        val link = File(desktop, "Shared")
        if (!Files.isSymbolicLink(link.toPath()) && !link.exists()) runCatching { Os.symlink(GUEST_PATH, link.path) }
        return host.path to GUEST_PATH
    }
}
