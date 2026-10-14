package app.pdftoolkit.mobile

/** English / Persian texts. `t("key")` follows the language chosen in Settings. */
object Strings {
    var lang: String = "en"

    private val table: Map<String, Pair<String, String>> = mapOf(
        "app" to ("PDF Toolkit" to "جعبه‌ابزار PDF"),
        "home.sub" to ("What do you want to do?" to "می‌خواهید چه کاری انجام دهید؟"),
        "settings" to ("Settings" to "تنظیمات"),
        "back" to ("Back" to "بازگشت"),
        "latex" to ("LaTeX editor" to "ویرایشگر لاتک"),
        "latex.sub" to ("Write and compile documents, offline" to "نوشتن و کامپایل سند، بدون اینترنت"),
        "merge" to ("Merge PDFs" to "ادغام PDF"),
        "split" to ("Split" to "جداسازی"),
        "organize" to ("Organize pages" to "مرتب‌سازی صفحه‌ها"),
        "compress" to ("Compress" to "فشرده‌سازی"),
        "convert" to ("Convert" to "تبدیل"),
        "ocr" to ("OCR" to "تشخیص متن (OCR)"),
        "protect" to ("Protect" to "رمزگذاری"),
        "soon" to ("Soon" to "به‌زودی"),
        "compile" to ("Compile" to "کامپایل"),
        "compiling" to ("Compiling…" to "در حال کامپایل…"),
        "editor" to ("Editor" to "ویرایشگر"),
        "preview" to ("PDF" to "PDF"),
        "templates" to ("Templates" to "قالب‌ها"),
        "undo" to ("Undo" to "واگرد"),
        "redo" to ("Redo" to "ازنو"),
        "log" to ("Log" to "گزارش"),
        "errors" to ("errors" to "خطا"),
        "ok" to ("Compiled" to "کامپایل شد"),
        "failed" to ("Compile failed" to "کامپایل ناموفق بود"),
        "engine.start" to ("Starting the TeX engine (first run takes longer)…" to "در حال راه‌اندازی موتور TeX (بار اول طولانی‌تر است)…"),
        "nopdf" to ("Compile to see the PDF here" to "برای دیدن PDF کامپایل کنید"),
        "mode" to ("Mode" to "حالت"),
        "light" to ("Light" to "روشن"),
        "dark" to ("Dark" to "تیره"),
        "style" to ("Design style" to "سبک طراحی"),
        "quiet" to ("Quiet Pro" to "آرام و حرفه‌ای"),
        "paper" to ("Paper" to "کاغذ"),
        "accent" to ("Accent colour" to "رنگ تأکید"),
        "language" to ("Language" to "زبان"),
        "tpl.article" to ("Article" to "مقاله"),
        "tpl.persian" to ("Persian article (XeLaTeX)" to "مقالهٔ فارسی (XeLaTeX)"),
        "tpl.report" to ("Report" to "گزارش"),
        "tpl.beamer" to ("Slides (Beamer)" to "اسلاید (Beamer)"),
        "tpl.blank" to ("Blank" to "خالی"),
        "symbols" to ("Symbols" to "نمادها"),
    )

    fun t(key: String): String {
        val p = table[key] ?: return key
        return if (lang == "fa") p.second else p.first
    }
}

fun t(key: String): String = Strings.t(key)
