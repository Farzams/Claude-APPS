package app.linuxpad

import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue
import app.linuxpad.display.Screens
import app.linuxpad.ui.AppRoot
import app.linuxpad.ui.LinuxPadTheme

class MainActivity : ComponentActivity() {
    companion object { var resumes by mutableIntStateOf(0) }   // bumped when the screen comes back, e.g. from a permission screen

    override fun onResume() { super.onResume(); resumes++ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)   // a long set-up must not be cut by the screen turning off
        setContent { LinuxPadTheme { AppRoot(Screens.read(this)) } }
    }
}
