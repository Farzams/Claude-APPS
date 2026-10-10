"""Help topics in English and Persian: {lang: [(title, body), ...]}. Paragraphs are separated by a blank line."""

EN = [
    ("Getting started", """
PDF Toolkit does the everyday jobs with PDFs and books in one place: read, OCR, extract text, convert, split, merge, compress, turn pictures into PDFs and edit pages.

Pick a tool from the list on the side, or click one of the cards on the Home page. Choose your file with Browse… or simply drag it onto the window.

Long jobs show a progress bar at the bottom. When a job finishes, the log tells you what happened and Open folder takes you to the result.

Everything is built in. Nothing else needs to be installed."""),
    ("Reading and searching", """
Open a PDF with Open PDF… or drag it onto the Read page. Use ◀ ▶ (or the arrow keys) to change page, − + to zoom and Fit to fit the page to the window. Ctrl + mouse wheel also zooms.

Type a word in the search box and press Enter. The app jumps to the next page that contains it and highlights the matches. Persian search ignores half-spaces (نیم‌فاصله) and different forms of the same letter, so «می‌شود» and «میشود» find each other.

Copy text copies the text of the current page. Persian text is repaired automatically so it pastes correctly into Word or a browser."""),
    ("OCR: scanned books", """
OCR adds an invisible text layer to scanned pages so you can search and copy them. The pictures of the pages are not changed.

Choose the language of the book (Persian is the first choice). Keep "Also recognise English words" ticked when the text mixes Persian and English, for example formulas, names and references.

Scan quality: 300 dpi is the best choice for normal books. Use 400 dpi for very small print and 200 dpi for a quick draft.

Pages that already contain text are skipped unless you untick the option. OCR of a long book can take a few minutes; the app uses all processor cores.

Tips for better results: straight, sharp, dark-on-light scans work best. Photos taken at an angle or with shadows reduce accuracy."""),
    ("Persian (Farsi) tips", """
Reading: the Read tab shows any PDF as it is. Searching and copying work on PDFs that contain real text, or after you run OCR on scans.

Converting: Word, ODT, RTF, EPUB, TXT and HTML files that contain Persian are shaped (letters joined) and laid out right-to-left automatically. Headings become bookmarks.

Old text files: files saved in Windows-1256 or UTF-16 are read correctly.

If you copy text from some older PDFs and it comes out backwards, use Extract text and tick "Fix backwards Persian/Arabic text".

Typing: some boxes in Windows cannot display joined Persian letters while you type. The app shows the correctly shaped text next to the search box. Searching still works normally."""),
    ("Extract text", """
Extract text saves the text of a PDF as a .txt file (UTF-8, opens correctly in Notepad) or a Word document. Persian paragraphs in the Word file are right-to-left.

Pages without text (scans) are read with OCR when "Read scanned pages with OCR" is ticked.

Persian letters in special presentation forms (ﻣﻘﺪﻣﻪ) are converted to normal letters (مقدمه) so the text can be searched anywhere."""),
    ("Convert to PDF", """
Add one or more files, choose the output folder and press Convert.

Works without extra software: EPUB, MOBI, FB2, XPS, CBZ, HTML, TXT, DOCX, ODT, RTF, Markdown, DjVu and common picture formats.

For ebooks you can choose page size and font size. A5 with size 11 is comfortable on a tablet.

Only very old formats (.doc, .lit, .pdb, .cbr) need the free program Calibre. The app tells you if that is the case."""),
    ("Split, Merge and Page tools", """
Split: cut a PDF by ranges (1-3, 5, 8- makes three files), every N pages, into N equal parts or one file per page.

Merge: add the PDFs, put them in order with ▲ ▼ and choose where to save.

Page tools: delete pages, keep only some pages, rotate pages or reverse the order. Page lists work like in the Split tool: 1-3, 7, 10-.

The original file is never changed; the result is saved as a new file."""),
    ("Compress", """
Four levels: Low keeps full quality and only tidies the file; Medium (150 dpi pictures) is good for most uses; High (110 dpi) and Extreme (72 dpi) give the smallest files.

The Ghostscript engine is strongest for scanned books. If a file cannot be made smaller, the original is kept so you never get a bigger file.

The result is saved as name_compressed.pdf next to your choice of folder."""),
    ("Images to PDF", """
Add many pictures, reorder them with ▲ ▼ and choose the page size: A4, A5, Letter or Fit to image (each page takes the size of its picture).

Photos from a phone are rotated correctly. Transparent PNG pictures get a white background.

Combine this with OCR to turn photos of book pages into a searchable PDF."""),
    ("Themes, pictures and language", """
Open Settings. Click a colour theme to apply it immediately: there are light and dark themes.

The picture at the top of every page can be changed: choose a style (Aurora, Waves, Mountains…) or pick your own photo with Choose my picture….

Language: choose English or فارسی. The app restarts to switch language; the Persian interface is laid out right-to-left."""),
    ("LaTeX and formulas", """
Open the LaTeX page to write or open a .tex file. Press Compile (or Ctrl+Enter): the PDF appears on the right, and any error is listed below with the line number and a plain-words hint. Click an error to jump to that line.

New from template gives you ready documents: article with theorems, Orlicz-space notes with notation macros, thesis, slides (Beamer), a Persian + English article, and chemistry and physics notes.

Import turns a Word, ODT, Markdown, EPUB or HTML file into a .tex file; equations stay as LaTeX.

Convert to PDF now typesets equations in Word, Markdown, ODT and EPUB files properly, also inside Persian documents. A .tex file can be converted directly.

The first compile may need internet to fetch a package; after that it is stored for offline use."""),
    ("Symbols, chemistry and physics", """
Press Symbols to open the palette: more than 300 symbols in groups (Greek letters, operators, relations, arrows, sets and logic, analysis, algebra, geometry, templates, physics, chemistry, units). Click a symbol to insert its LaTeX at the cursor in the editor or the Formula box. Right-click copies it instead. Use the search box to find a symbol by name, for example integral, alpha or norm.

The Analysis group has notation for Orlicz spaces: Lᶲ, Luxemburg norm, Δ₂ and ∇₂ conditions, modular, convolution, Fourier transform.

Chemistry: write reactions with \\ce{2H2 + O2 -> 2H2O}, ions with \\ce{Fe^{3+}} and structure drawings with \\chemfig{*6(=-=-=-)}. Physics: units with \\SI{9.81}{m/s^2}, bra-ket and derivatives with the physics package.

The Formula page turns one formula into a PNG, SVG or PDF with a transparent background and your chosen colour; use white for dark slides."""),
    ("Questions and problems", """
The app feels slow? Close big files in other programs; the window hides its content for a moment while you drag its edge, which keeps resizing smooth.

OCR found nothing? Check the language and try 400 dpi. Very dark or blurry scans need better photos.

"Password protected" message: the PDF is encrypted. Remove the password with the program that created it first.

Windows says the app is unknown: it is not digitally signed. Choose More info, then Run anyway.

Your settings are stored in the folder %APPDATA%\\PDFToolkit."""),
    ("About and licences", """
PDF Toolkit uses these free programs, each running separately and unmodified: PyMuPDF (reading, layout), Tesseract (OCR), Ghostscript (compression), DjVuLibre (DjVu), Pandoc (Word/ODT/RTF/EPUB).

Fonts: Noto Sans Arabic (SIL Open Font License) and DejaVu Sans. Full licence texts are in the fonts folder and in the project README."""),
]

FA = [
    ("شروع کار", """
جعبه‌ابزار PDF کارهای روزمرهٔ PDF و کتاب را یک‌جا انجام می‌دهد: مطالعه، OCR، استخراج متن، تبدیل، جداسازی، ادغام، فشرده‌سازی، ساخت PDF از تصویر و ویرایش صفحه‌ها.

یکی از ابزارها را از فهرست کناری انتخاب کنید یا روی یکی از کارت‌های صفحهٔ خانه بزنید. فایل را با «مرور…» انتخاب کنید یا فقط روی پنجره بکشید و رها کنید.

در کارهای طولانی نوار پیشرفت پایین صفحه نمایش داده می‌شود. پس از پایان، گزارش نتیجه را می‌بینید و با «باز کردن پوشه» به فایل خروجی می‌رسید.

همه‌چیز داخل برنامه است و به نصب چیز دیگری نیاز ندارید."""),
    ("مطالعه و جست‌وجو", """
یک PDF را با «باز کردن PDF…» یا با کشیدن روی صفحهٔ مطالعه باز کنید. با ◀ ▶ (یا کلیدهای جهت‌دار) صفحه را عوض کنید، با − + بزرگ‌نمایی کنید و با «تنظیم» صفحه را به پهنای پنجره برسانید. Ctrl + چرخ ماوس هم بزرگ‌نمایی می‌کند.

کلمه‌ای را در کادر جست‌وجو بنویسید و Enter بزنید. برنامه به صفحهٔ بعدی که آن کلمه را دارد می‌رود و نتیجه‌ها را رنگی می‌کند. جست‌وجوی فارسی نیم‌فاصله و شکل‌های مختلف یک حرف را نادیده می‌گیرد؛ پس «می‌شود» و «میشود» همدیگر را پیدا می‌کنند.

«کپی متن» متن صفحهٔ جاری را کپی می‌کند. متن فارسی خودکار اصلاح می‌شود تا در ورد یا مرورگر درست جایگذاری شود."""),
    ("OCR: کتاب‌های اسکن‌شده", """
OCR یک لایهٔ نامرئی متن به صفحه‌های اسکن‌شده می‌افزاید تا بتوانید در آن‌ها جست‌وجو و از آن‌ها کپی کنید. تصویر صفحه‌ها تغییر نمی‌کند.

زبان کتاب را انتخاب کنید (فارسی گزینهٔ اول است). وقتی متن فارسی و انگلیسی با هم است، مثل فرمول‌ها، نام‌ها و منابع، گزینهٔ «کلمه‌های انگلیسی را هم بشناس» را روشن نگه دارید.

کیفیت اسکن: برای کتاب‌های معمولی ۳۰۰ dpi بهترین انتخاب است. برای چاپ بسیار ریز ۴۰۰ و برای پیش‌نویس سریع ۲۰۰ را بزنید.

صفحه‌هایی که از قبل متن دارند رد می‌شوند، مگر این گزینه را خاموش کنید. OCR یک کتاب بلند چند دقیقه طول می‌کشد؛ برنامه از همهٔ هسته‌های پردازنده استفاده می‌کند.

برای نتیجهٔ بهتر: اسکن صاف، واضح و با نوشتهٔ تیره روی زمینهٔ روشن بهترین است. عکس کج یا همراه با سایه دقت را کم می‌کند."""),
    ("نکته‌هایی برای فارسی", """
مطالعه: برگهٔ «مطالعه» هر PDF را همان‌طور که هست نشان می‌دهد. جست‌وجو و کپی در PDFهایی کار می‌کند که متن واقعی دارند، یا بعد از اجرای OCR روی اسکن‌ها.

تبدیل: فایل‌های ورد، ODT، RTF، EPUB، TXT و HTML که فارسی دارند خودکار حرف‌به‌حرف به هم چسبیده و راست‌به‌چپ چیده می‌شوند. عنوان‌ها به نشانک (bookmark) تبدیل می‌شوند.

فایل‌های قدیمی: فایل‌های متنی با کدگذاری Windows-1256 یا UTF-16 درست خوانده می‌شوند.

اگر متن بعضی PDFهای قدیمی هنگام کپی وارونه درمی‌آید، از «استخراج متن» استفاده کنید و «اصلاح متن وارونه» را بزنید.

تایپ: بعضی کادرهای ویندوز هنگام تایپ نمی‌توانند حرف‌های فارسی را چسبیده نشان دهند. برنامه متن درست‌شده را کنار کادر جست‌وجو نشان می‌دهد و جست‌وجو طبق معمول کار می‌کند."""),
    ("استخراج متن", """
«استخراج متن» متن یک PDF را به‌صورت فایل txt (با UTF-8، در Notepad درست باز می‌شود) یا سند ورد ذخیره می‌کند. بندهای فارسی در فایل ورد راست‌به‌چپ‌اند.

صفحه‌های بدون متن (اسکن) اگر «صفحه‌های اسکن‌شده را با OCR بخوان» روشن باشد با OCR خوانده می‌شوند.

حرف‌هایی که به شکل‌های ویژهٔ نمایشی هستند (ﻣﻘﺪﻣﻪ) به حرف‌های معمولی (مقدمه) تبدیل می‌شوند تا متن در همه‌جا قابل جست‌وجو باشد."""),
    ("تبدیل به PDF", """
یک یا چند فایل را اضافه کنید، پوشهٔ خروجی را انتخاب کنید و «تبدیل» را بزنید.

بدون نرم‌افزار اضافه کار می‌کند: EPUB، MOBI، FB2، XPS، CBZ، HTML، TXT، DOCX، ODT، RTF، Markdown، DjVu و قالب‌های رایج تصویر.

برای کتاب‌های الکترونیکی می‌توانید اندازهٔ صفحه و اندازهٔ قلم را انتخاب کنید. A5 با اندازهٔ ۱۱ برای تبلت راحت است.

فقط قالب‌های خیلی قدیمی (doc، lit، pdb، cbr) به برنامهٔ رایگان Calibre نیاز دارند و برنامه در این مورد به شما خبر می‌دهد."""),
    ("جداسازی، ادغام و ابزار صفحات", """
جداسازی: PDF را با بازه (۱-۳، ۵، ۸- سه فایل می‌سازد)، هر N صفحه، به N بخش مساوی یا هر صفحه در یک فایل می‌برد.

ادغام: PDFها را اضافه کنید، با ▲ ▼ ترتیبشان را بدهید و محل ذخیره را انتخاب کنید.

ابزار صفحات: حذف صفحه، نگه‌داشتن چند صفحه، چرخاندن صفحه یا وارونه کردن ترتیب. فهرست صفحه‌ها مثل ابزار جداسازی نوشته می‌شود: 1-3, 7, 10-

فایل اصلی هرگز تغییر نمی‌کند و نتیجه در فایل تازه‌ای ذخیره می‌شود."""),
    ("فشرده‌سازی", """
چهار سطح دارد: «کم» کیفیت را کامل نگه می‌دارد و فقط فایل را مرتب می‌کند؛ «متوسط» (تصویر ۱۵۰ dpi) برای بیشتر کارها خوب است؛ «زیاد» (۱۱۰ dpi) و «بیشترین» (۷۲ dpi) کوچک‌ترین فایل را می‌دهند.

موتور Ghostscript برای کتاب‌های اسکن‌شده قوی‌ترین است. اگر فایل کوچک‌تر نشود، فایل اصلی نگه داشته می‌شود تا هرگز فایل بزرگ‌تر نگیرید.

نتیجه با نام name_compressed.pdf در پوشه‌ای که انتخاب کرده‌اید ذخیره می‌شود."""),
    ("تصویر به PDF", """
چندین تصویر را اضافه کنید، با ▲ ▼ ترتیب بدهید و اندازهٔ صفحه را انتخاب کنید: A4، A5، Letter یا «هم‌اندازهٔ تصویر» (هر صفحه به اندازهٔ تصویرش می‌شود).

عکس‌های موبایل درست چرخانده می‌شوند و تصویرهای PNG شفاف زمینهٔ سفید می‌گیرند.

با OCR ترکیبش کنید تا عکس صفحه‌های کتاب به PDF قابل جست‌وجو تبدیل شود."""),
    ("تم، تصویر و زبان", """
«تنظیمات» را باز کنید. روی یک تم رنگی بزنید تا فوراً اعمال شود؛ تم روشن و تیره دارید.

تصویر بالای هر صفحه را می‌توانید عوض کنید: یک سبک (شفق، موج، کوه…) انتخاب کنید یا با «انتخاب تصویر من…» عکس خودتان را بگذارید.

زبان: English یا فارسی را انتخاب کنید. برای تغییر زبان برنامه دوباره باز می‌شود و رابط فارسی راست‌به‌چپ چیده می‌شود."""),
    ("لاتک و فرمول‌ها", """
صفحهٔ «لاتک» را باز کنید تا فایل tex بنویسید یا باز کنید. «کامپایل» (یا Ctrl+Enter) را بزنید: PDF سمت راست نمایش داده می‌شود و هر خطا همراه با شمارهٔ خط و یک راهنمای ساده پایین فهرست می‌شود. روی خطا بزنید تا به همان خط بروید.

«جدید از قالب» سندهای آماده می‌دهد: مقاله با قضیه، یادداشت‌های فضاهای اورلیچ با میانبرهای نمادگذاری، پایان‌نامه، اسلاید (Beamer)، مقالهٔ فارسی + انگلیسی و یادداشت‌های شیمی و فیزیک.

«درون‌ریزی» فایل ورد، ODT، Markdown، EPUB یا HTML را به فایل tex تبدیل می‌کند و معادله‌ها به‌صورت لاتک می‌مانند.

«تبدیل به PDF» حالا معادله‌ها را در فایل‌های ورد، Markdown، ODT و EPUB درست حروف‌چینی می‌کند، حتی داخل سندهای فارسی. فایل tex را هم می‌توان مستقیم تبدیل کرد.

اولین کامپایل ممکن است برای گرفتن یک بسته به اینترنت نیاز داشته باشد؛ بعد از آن برای استفادهٔ آفلاین ذخیره می‌شود."""),
    ("نمادها، شیمی و فیزیک", """
«نمادها» را بزنید تا پالت باز شود: بیش از ۳۰۰ نماد در گروه‌ها (حروف یونانی، عملگرها، رابطه‌ها، پیکان‌ها، مجموعه و منطق، آنالیز، جبر، هندسه، قالب‌ها، فیزیک، شیمی، یکاها). روی یک نماد بزنید تا لاتک آن در جای مکان‌نما در ویرایشگر یا کادر فرمول درج شود. با راست‌کلیک فقط کپی می‌شود. با کادر جست‌وجو نماد را از روی نامش پیدا کنید، مثلاً integral، alpha یا norm.

گروه «آنالیز» نمادگذاری فضاهای اورلیچ را دارد: Lᶲ، نرم لوکزامبورگ، شرط‌های Δ₂ و ∇₂، مدولار، کانولوشن و تبدیل فوریه.

شیمی: واکنش‌ها را با \\ce{2H2 + O2 -> 2H2O}، یون‌ها را با \\ce{Fe^{3+}} و ساختارها را با \\chemfig{*6(=-=-=-)} بنویسید. فیزیک: یکاها با \\SI{9.81}{m/s^2} و براکت‌ها و مشتق‌ها با بستهٔ physics.

صفحهٔ «فرمول» یک فرمول را با زمینهٔ شفاف و رنگ دلخواه به PNG، SVG یا PDF تبدیل می‌کند؛ برای اسلاید تیره رنگ سفید را بزنید."""),
    ("پرسش‌ها و مشکل‌ها", """
برنامه کند است؟ فایل‌های بزرگ را در برنامه‌های دیگر ببندید. هنگام کشیدن لبهٔ پنجره، محتوا لحظه‌ای پنهان می‌شود تا تغییر اندازه روان بماند.

OCR چیزی پیدا نکرد؟ زبان را بررسی کنید و ۴۰۰ dpi را امتحان کنید. اسکن‌های خیلی تیره یا تار به عکس بهتری نیاز دارند.

پیام «رمزدار است»: PDF رمز دارد. ابتدا رمز را با برنامه‌ای که ساخته برداشید.

ویندوز می‌گوید برنامه ناشناس است: برنامه امضای دیجیتال ندارد. «More info» و سپس «Run anyway» را بزنید.

تنظیمات شما در پوشهٔ %APPDATA%\\PDFToolkit ذخیره می‌شود."""),
    ("دربارهٔ برنامه و مجوزها", """
جعبه‌ابزار PDF از این برنامه‌های رایگان استفاده می‌کند که هر کدام جدا و بدون تغییر اجرا می‌شوند: PyMuPDF (خواندن و صفحه‌آرایی)، Tesseract (OCR)، Ghostscript (فشرده‌سازی)، DjVuLibre (DjVu) و Pandoc (ورد/ODT/RTF/EPUB).

قلم‌ها: Noto Sans Arabic (مجوز SIL Open Font) و DejaVu Sans. متن کامل مجوزها در پوشهٔ fonts و فایل README پروژه است."""),
]

TOPICS = {"en": EN, "fa": FA}
