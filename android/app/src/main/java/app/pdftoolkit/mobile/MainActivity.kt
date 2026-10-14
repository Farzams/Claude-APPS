package app.pdftoolkit.mobile

import android.os.Bundle
import android.widget.FrameLayout
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.platform.ComposeView
import androidx.compose.material3.MaterialTheme
import androidx.core.view.WindowCompat

@OptIn(androidx.compose.ui.ExperimentalComposeUiApi::class)
class MainActivity : ComponentActivity() {
    private val editor: EditorViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val prefs = Prefs(this)
        Strings.lang = prefs.lang

        val root = FrameLayout(this)
        val compose = ComposeView(this)
        root.addView(compose, FrameLayout.LayoutParams(-1, -1))
        setContentView(root)
        TexEngine.attach(this, root)          // hidden 1x1 WebView that runs the TeX engine

        compose.setContent {
            var themeKey by remember { mutableStateOf(prefs.theme) }
            var accent by remember { mutableStateOf(prefs.accent) }
            var lang by remember { mutableStateOf(prefs.lang) }
            var screen by rememberSaveable { mutableStateOf("home") }
            // bump to recompose texts after a language change
            var tick by remember { mutableIntStateOf(0) }
            Strings.lang = lang
            val refresh = {
                themeKey = prefs.theme; accent = prefs.accent; lang = prefs.lang; Strings.lang = prefs.lang; tick++
            }
            AppTheme(paletteOf(themeKey), accent, lang == "fa") {
                androidx.compose.foundation.layout.Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background).imePadding().semantics { testTagsAsResourceId = true }) {
                    if (tick >= 0) when (screen) {
                        "latex" -> EditorScreen(editor, { screen = "home" }, prefs.editorSize)
                        "settings" -> SettingsScreen(prefs, refresh) { screen = "home" }
                        else -> HomeScreen({ screen = it }, { screen = "settings" })
                    }
                }
            }
            BackHandler(enabled = screen != "home") { screen = "home" }
        }
    }
}
