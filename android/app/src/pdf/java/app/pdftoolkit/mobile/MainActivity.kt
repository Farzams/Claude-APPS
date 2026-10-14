package app.pdftoolkit.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.core.view.WindowCompat

@OptIn(androidx.compose.ui.ExperimentalComposeUiApi::class)
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        PdfOps.init(this)
        val prefs = Prefs(this)
        Strings.lang = prefs.lang

        setContent {
            var themeKey by remember { mutableStateOf(prefs.theme) }
            var accent by remember { mutableStateOf(prefs.accent) }
            var lang by remember { mutableStateOf(prefs.lang) }
            var screen by rememberSaveable { mutableStateOf("home") }
            var tick by remember { mutableIntStateOf(0) }
            Strings.lang = lang
            val refresh: () -> Unit = {
                themeKey = prefs.theme; accent = prefs.accent; lang = prefs.lang; Strings.lang = prefs.lang; tick++
            }
            val home = { screen = "home" }
            val picker = remember { FilePicker() }
            AppTheme(paletteOf(themeKey), accent, lang == "fa") {
                Box(Modifier.fillMaxSize().themeBackground().semantics { testTagsAsResourceId = true }) {
                    FilePickerHost(picker) { AnimatedContent(
                        targetState = screen, label = "screen",
                        transitionSpec = {
                            if (targetState == "home" || targetState == "files") fadeIn(tween(180)) togetherWith fadeOut(tween(120))
                            else (fadeIn(tween(200)) + slideInHorizontally(tween(220)) { it / 10 }) togetherWith fadeOut(tween(120))
                        },
                    ) { s ->
                        if (tick >= 0) when (s) {
                            "merge" -> MergeScreen(home)
                            "split" -> SplitScreen(home)
                            "organize" -> OrganizeScreen(home)
                            "compress" -> CompressScreen(home)
                            "img2pdf" -> PicturesToPdfScreen(home)
                            "pdf2img" -> PdfToPicturesScreen(home)
                            "protect" -> ProtectScreen(home)
                            "watermark" -> WatermarkScreen(home)
                            "numbers" -> NumbersScreen(home)
                            "docs2pdf" -> ConvertScreen(home)
                            "settings" -> SettingsScreen(prefs, refresh, { screen = "home" }, tagline = t("about.tag.pdf")) { FilesSettingsCard() }
                            "files" -> PdfShell("files", { screen = it }) { FilesScreen { screen = it } }
                            else -> PdfShell("home", { screen = it }) { HomeScreen { screen = it } }
                        }
                    } }
                }
            }
            BackHandler(enabled = screen != "home") { screen = "home" }
        }
    }
}
