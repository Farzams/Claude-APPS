package app.pdftoolkit.mobile

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import java.io.File

enum class PickKind { OPEN, SAVE, FOLDER }

/** One thing the app asks the file manager for: pick files, pick a place and a name to save to, or pick a folder. */
class PickRequest(
    val kind: PickKind,
    val allowed: Set<Kind>?,          // null = any file
    val multi: Boolean,
    val suggestedName: String,
    val mime: String,
    val start: File?,
    val onResult: (List<Uri>) -> Unit,
)

/** The file manager that opens on top of the app. Screens ask it for files instead of calling Android's own picker. */
class FilePicker {
    var request by mutableStateOf<PickRequest?>(null)

    fun open(allowed: Set<Kind>?, multi: Boolean, start: File?, onResult: (List<Uri>) -> Unit) {
        request = PickRequest(PickKind.OPEN, allowed, multi, "", "*/*", start, onResult)
    }

    fun save(name: String, mime: String, start: File?, onResult: (Uri) -> Unit) {
        request = PickRequest(PickKind.SAVE, null, false, name, mime, start) { onResult(it.first()) }
    }

    fun folder(start: File?, onResult: (Uri) -> Unit) {
        request = PickRequest(PickKind.FOLDER, null, false, "", "*/*", start) { onResult(it.first()) }
    }
}

val LocalFilePicker = staticCompositionLocalOf { FilePicker() }

/** Works like Android's activity-result launchers: build once, call launch(input). */
class Launcher<I>(private val run: (I) -> Unit) {
    fun launch(input: I) = run(input)
}

/** Kinds of files that go with a list of MIME types such as arrayOf("application/pdf"). */
fun kindsOf(mimes: Array<String>): Set<Kind>? {
    if (mimes.any { it == "*/*" || it == "application/octet-stream" || it.startsWith("text/") }) return null
    val out = HashSet<Kind>()
    for (m in mimes) when {
        m == "application/pdf" -> out.add(Kind.PDF)
        m.startsWith("image/") -> out.add(Kind.IMAGE)
        m == "application/zip" -> out.add(Kind.ARCHIVE)
    }
    return out.ifEmpty { null }
}

private fun mimesOf(allowed: Set<Kind>?): Array<String> = when {
    allowed == null -> arrayOf("*/*")
    allowed == setOf(Kind.PDF) -> arrayOf("application/pdf")
    allowed == setOf(Kind.IMAGE) -> arrayOf("image/*")
    else -> arrayOf("*/*")
}

@Composable
fun rememberMultiPicker(onPicked: (List<Uri>) -> Unit): Launcher<Array<String>> {
    val picker = LocalFilePicker.current
    val cb by rememberUpdatedState(onPicked)
    return remember(picker) { Launcher { mimes -> picker.open(kindsOf(mimes), true, FileMemory.startFor(null)) { cb(it) } } }
}

@Composable
fun rememberAnyPicker(near: () -> Uri? = { null }, onPicked: (Uri?) -> Unit): Launcher<Array<String>> {
    val picker = LocalFilePicker.current
    val cb by rememberUpdatedState(onPicked)
    val nearNow by rememberUpdatedState(near)
    return remember(picker) { Launcher { mimes -> picker.open(kindsOf(mimes), false, FileMemory.startFor(nearNow())) { cb(it.firstOrNull()) } } }
}

@Composable
fun rememberSavePicker(mime: String, near: () -> Uri? = { null }, onSaved: (Uri?) -> Unit): Launcher<String> {
    val picker = LocalFilePicker.current
    val cb by rememberUpdatedState(onSaved)
    val nearNow by rememberUpdatedState(near)
    return remember(picker, mime) { Launcher { name -> picker.save(name, mime, FileMemory.startFor(nearNow())) { cb(it) } } }
}

@Composable
fun rememberFolderPicker(near: () -> Uri? = { null }, onPicked: (Uri?) -> Unit): Launcher<Unit?> {
    val picker = LocalFilePicker.current
    val cb by rememberUpdatedState(onPicked)
    val nearNow by rememberUpdatedState(near)
    return remember(picker) { Launcher { picker.folder(FileMemory.startFor(nearNow())) { cb(it) } } }
}

/**
 * Hosts the file manager on top of [content]. If the person has not allowed "All files access" they can still
 * fall back to Android's own picker from the manager's permission page.
 */
@Composable
fun FilePickerHost(picker: FilePicker, content: @Composable () -> Unit) {
    val ctx = androidx.compose.ui.platform.LocalContext.current
    val memory = remember { FileMemory(ctx) }
    LaunchedFilesMemory.set(memory)

    fun finish(uris: List<Uri>) {
        val r = picker.request
        picker.request = null
        if (r != null && uris.isNotEmpty()) r.onResult(uris)
    }

    val openMany = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { finish(it) }
    val openOne = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { finish(listOfNotNull(it)) }
    val savePdf = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/pdf")) { finish(listOfNotNull(it)) }
    val saveAny = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/octet-stream")) { finish(listOfNotNull(it)) }
    val tree = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocumentTree()) { finish(listOfNotNull(it)) }

    CompositionLocalProvider(LocalFilePicker provides picker) {
        Box(Modifier.fillMaxSize()) {
            content()
            val r = picker.request
            if (r != null) {
                FileBrowserOverlay(
                    request = r,
                    memory = memory,
                    onClose = { picker.request = null },
                    onDone = { files -> finish(files.map { Uri.fromFile(it) }) },
                    onUseSystemPicker = {
                        when (r.kind) {
                            PickKind.OPEN -> if (r.multi) openMany.launch(mimesOf(r.allowed)) else openOne.launch(mimesOf(r.allowed))
                            PickKind.SAVE -> if (r.mime == "application/pdf") savePdf.launch(r.suggestedName) else saveAny.launch(r.suggestedName)
                            PickKind.FOLDER -> tree.launch(null)
                        }
                    },
                )
            }
        }
    }
}

/** The file manager's memory is created by the host; the pickers read the last folder from it. */
object LaunchedFilesMemory {
    private var memory: FileMemory? = null
    fun set(m: FileMemory) { memory = m }
    fun get(): FileMemory? = memory
}
