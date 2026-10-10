"""Help topics in English and Persian: {lang: [(title, body), ...]}. Paragraphs are separated by a blank line."""

EN = [
    ("Getting started", """
PDF Toolkit does the everyday jobs with PDFs and books in one place: read, OCR, extract text, convert, split, merge, compress, turn pictures into PDFs and edit pages.

Pick a tool from the list on the side, or click one of the cards on the Home page. Choose your file with Browse… or simply drag it onto the window.

Long jobs show a progress bar at the bottom. When a job finishes, the log tells you what happened and Open folder takes you to the result.

Everything is built in. Nothing else needs to be installed."""),
    ("Reading and searching", """
Open any book or document with Open… (Ctrl+O) or drag it onto the Read page: PDF, DjVu, EPUB, MOBI/AZW, FB2, CBZ, XPS, DOCX, ODT, RTF, Markdown, HTML, TXT, TeX and pictures. Formats that are not PDF are converted once in the background and remembered, so they open instantly next time.

Every file opens in its own tab. Pages scroll continuously. Use the buttons on top or the keyboard: PageUp/PageDown or Space to move, Ctrl + mouse wheel or Ctrl + / Ctrl − to zoom, Ctrl+0 to fit the width, Ctrl+G to jump to a page, F11 for full screen.

The side panel has page thumbnails, the table of contents, your bookmarks (Ctrl+D) and search results. Search (Ctrl+F) shows every page that contains the word and highlights the matches. Persian search ignores half-spaces and different forms of the same letter, so «می‌شود» and «میشود» find each other.

Reading colours: light, sepia (paper) or night. Two-page view and a right-to-left switch are meant for books and manga. For e-books (EPUB, MOBI, FB2, TXT) the text size can be changed with Aa − / +.

Select text by dragging over it; it is copied automatically. Click a link inside the book to follow it. The app remembers your page, zoom and bookmarks for every book."""),
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
    ("PDF tools: organize, edit, protect", """
All tools are listed in All tools (type to search).

Organize pages: drag the thumbnails to reorder; rotate, delete, duplicate, extract or insert pages from another PDF or picture; Undo goes back step by step. Crop pages trims white margins automatically or cuts a fixed margin. Delete blank pages finds empty pages, also nearly-white scans.

Edit PDF: replace text (Persian works), add text or a picture inside a box you draw, replace or remove a picture. Header, footer & Bates adds page numbers, dates, file names and Bates numbers. Watermark stamps text or a picture at any angle. Page background paints a colour or picture behind the content.

PDF to…: pictures (PNG, JPEG, TIFF), Word, Excel (tables), HTML, RTF, EPUB or text. The Word export keeps text, pictures and right-to-left direction but simplifies the exact layout. Scanned PDFs: tick the OCR option first.

Password & permissions: protects with AES-256 and can forbid printing, copying or editing. A forgotten password cannot be recovered. Remove hidden data cleans author names, comments, attachments and scripts. Redact black out words, patterns (e-mail, phone, card numbers) or drawn areas — the text under the black is deleted for good.

Compare PDFs shows what changed, as text and as a picture with differences in red. Batch process runs one operation on a whole list of files."""),
    ("Math and spell-check", """
Math (in the side list, and in Math Studio) is an exact calculator. Type ordinary maths: x^2, 2x, sin(x)/x, sqrt(2), pi, e, oo for infinity — or paste LaTeX such as \\frac{x^2-1}{x-1}. Choose what to do: simplify, expand, factor, derivative, integral (leave the limits empty for an indefinite integral), limit, Taylor series, sum, equations and systems (one per line), differential equations (write y'' + y = 0), matrices (determinant, inverse, eigenvalues…) and plots. Every answer is shown as a formula and can be copied as LaTeX or inserted into the LaTeX page. A hard problem is stopped after 90 seconds.

Spell-check in the LaTeX page underlines misspelled English and Persian words with a red wave; commands, formulas, labels and comments are skipped. Right-click a word for suggestions, Add to dictionary or Ignore. The tick box under the editor turns it off. Common names of mathematicians (Banach, Hilbert, Fourier…) are already known."""),
    ("Look, Settings and Ctrl+K search", """
Press Ctrl+K anywhere to open the search box. Type a few letters of a tool ("water", "merge"), a setting ("dark", "icons"), or the name of a book you opened before, then press Enter.

Settings > Appearance: choose Light, Dark or Match Windows; a design style (Quiet Pro is flat and calm, Paper is warm like a book, Classic keeps the picture backgrounds); an accent colour for buttons and links; any of the 13 colour themes; one of four icon styles; the text size; and the Persian font.

The three programs (PDF Toolkit, Reader, Math Studio) have flat colour icons: indigo, teal and magenta.

Settings > Storage shows how much space the Reader cache and the LaTeX packages use, and clears them. Nothing you save is touched.
"""),
    ("Add-ons and separate windows", """
Settings has an Add-ons section. Add-ons are optional downloads that stay on your computer and work offline afterwards: Formula OCR (a picture of a printed formula becomes LaTeX; always check the result — it may confuse symbols such as n and π) and More LaTeX packages (hundreds more packages, classes and fonts that compile without internet). Install or Remove with one click; the list needs internet only to download.

One installation gives three start-menu apps: PDF Toolkit (everything), PDF Toolkit Reader (only the reader, with a slim side bar) and Math Studio (Math, Formula from picture, LaTeX and Formula). They share the same files, so they need no extra space. In the portable version use Reader.bat and MathStudio.bat. During installation you can add the Reader to the Open with list of DjVu, EPUB, MOBI, FB2, CBZ and XPS files.

Clean scans straightens crooked pages, removes shadows and noise and can make black-and-white pages with small files; run OCR afterwards. Repair & optimize rebuilds a damaged PDF that will not open."""),
    ("Themes, pictures and language", """
Open Settings. Click a colour theme to apply it immediately: there are light and dark themes.

The picture behind the whole window can be changed: choose a style (Aurora, Waves, Mountains…) or pick your own photo with Choose my picture…. The Medium / Vivid setting controls how much of the picture shows through the cards.

Language: choose English or فارسی. The app restarts to switch language; the Persian interface is laid out right-to-left."""),
    ("LaTeX and formulas", """
Open the LaTeX page to write or open a .tex file. Press Compile (or Ctrl+Enter): the PDF appears on the right, and any error is listed below with the line number and a plain-words hint. Click an error to jump to that line.

New from template gives you ready documents: article with theorems, thesis, slides (Beamer), a Persian + English article, and chemistry and physics notes.

Import turns a Word, ODT, Markdown, EPUB or HTML file into a .tex file; equations stay as LaTeX.

Convert to PDF now typesets equations in Word, Markdown, ODT and EPUB files properly, also inside Persian documents. A .tex file can be converted directly.

The first compile may need internet to fetch a package; after that it is stored for offline use."""),
    ("Symbols, chemistry and physics", """
Press Symbols to open the palette: more than 300 symbols in groups (Greek letters, operators, relations, arrows, sets and logic, analysis, algebra, geometry, templates, physics, chemistry, units). Click a symbol to insert its LaTeX at the cursor in the editor or the Formula box. Right-click copies it instead. Use the search box to find a symbol by name, for example integral, alpha or norm.

The Analysis group has notation for function spaces and norms, derivatives, integrals, convolution and the Fourier transform.

Chemistry: write reactions with \\ce{2H2 + O2 -> 2H2O}, ions with \\ce{Fe^{3+}} and structure drawings with \\chemfig{*6(=-=-=-)}. Physics: units with \\SI{9.81}{m/s^2}, bra-ket and derivatives with the physics package.

The Formula page turns one formula into a PNG, SVG or PDF with a transparent background and your chosen colour; use white for dark slides."""),
    ("Questions and problems", """
The app feels slow? Close big files in other programs. Long jobs such as OCR of a whole book run in the background and use all processor cores; the window stays responsive while they work.

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
هر کتاب یا سندی را با «باز کردن…» (Ctrl+O) یا کشیدن روی صفحهٔ مطالعه باز کنید: PDF، DjVu، EPUB، MOBI/AZW، FB2، CBZ، XPS، DOCX، ODT، RTF، Markdown، HTML، TXT، TeX و تصویر. قالب‌هایی که PDF نیستند یک‌بار در پس‌زمینه تبدیل و به خاطر سپرده می‌شوند، پس دفعهٔ بعد فوراً باز می‌شوند.

هر فایل در زبانهٔ خودش باز می‌شود. صفحه‌ها پیوسته پیمایش می‌شوند. از دکمه‌های بالا یا صفحه‌کلید استفاده کنید: PageUp/PageDown یا فاصله برای حرکت، Ctrl + چرخ ماوس یا Ctrl + / Ctrl − برای بزرگ‌نمایی، Ctrl+0 برای هم‌عرض‌شدن، Ctrl+G برای رفتن به صفحه و F11 برای تمام‌صفحه.

نوار کناری تصویر بندانگشتی صفحه‌ها، فهرست مطالب، نشانک‌های شما (Ctrl+D) و نتایج جست‌وجو را دارد. جست‌وجو (Ctrl+F) همهٔ صفحه‌های دارای واژه را نشان می‌دهد و موارد را پررنگ می‌کند. جست‌وجوی فارسی نیم‌فاصله و شکل‌های مختلف یک حرف را نادیده می‌گیرد، پس «می‌شود» و «میشود» همدیگر را پیدا می‌کنند.

رنگ مطالعه: روشن، کاغذی یا شب. نمای دو صفحه‌ای و کلید راست‌به‌چپ برای کتاب و مانگا است. در کتاب‌های الکترونیکی (EPUB، MOBI، FB2، TXT) اندازهٔ متن با Aa − / + تغییر می‌کند.

با کشیدن روی متن آن را انتخاب کنید؛ خودکار کپی می‌شود. روی پیوندهای داخل کتاب کلیک کنید تا باز شوند. برنامه صفحه، بزرگ‌نمایی و نشانک‌های هر کتاب را به خاطر می‌سپارد."""),
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
    ("ابزارهای PDF: مرتب‌سازی، ویرایش، حفاظت", """
همهٔ ابزارها در «همهٔ ابزارها» فهرست شده‌اند (برای جست‌وجو تایپ کنید).

مرتب‌سازی صفحه‌ها: تصویرهای بندانگشتی را بکشید تا جابه‌جا شوند؛ بچرخانید، حذف، تکثیر، استخراج یا از PDF و تصویر دیگر درج کنید؛ «واگرد» قدم‌به‌قدم برمی‌گردد. برش صفحه‌ها حاشیهٔ سفید را خودکار می‌برد یا حاشیهٔ ثابتی را. حذف صفحه‌های خالی صفحه‌های خالی و اسکن‌های تقریباً سفید را پیدا می‌کند.

ویرایش PDF: جایگزینی متن (فارسی هم کار می‌کند)، افزودن متن یا تصویر داخل جعبه‌ای که می‌کشید، تعویض یا حذف تصویر. سرصفحه، پاصفحه و باتس شمارهٔ صفحه، تاریخ، نام فایل و شمارهٔ باتس می‌افزاید. واترمارک متن یا تصویر را با هر زاویه می‌زند. پس‌زمینهٔ صفحه رنگ یا تصویری پشت محتوا می‌گذارد.

PDF به…: تصویر (PNG، JPEG، TIFF)، ورد، اکسل (جدول‌ها)، HTML، RTF، EPUB یا متن. خروجی ورد متن، تصویر و جهت راست‌به‌چپ را نگه می‌دارد ولی چیدمان دقیق را ساده می‌کند. برای PDF اسکن‌شده اول گزینهٔ OCR را تیک بزنید.

گذرواژه و دسترسی‌ها: با AES-256 محافظت می‌کند و می‌تواند چاپ، کپی یا ویرایش را ممنوع کند. گذرواژهٔ فراموش‌شده بازیابی نمی‌شود. حذف داده‌های پنهان نام نویسنده، نظرها، پیوست‌ها و اسکریپت‌ها را پاک می‌کند. سانسور واژه‌ها، الگوها (ایمیل، تلفن، کارت) یا ناحیه‌های کشیده‌شده را می‌پوشاند — متن زیر نوار سیاه برای همیشه پاک می‌شود.

مقایسهٔ PDFها نشان می‌دهد چه چیزی تغییر کرده، هم متنی و هم تصویری با تفاوت‌های قرمز. پردازش دسته‌ای یک عملیات را روی فهرستی از فایل‌ها اجرا می‌کند."""),
    ("ریاضی و غلط‌یاب", """
«ریاضی» (در فهرست کناری و در استودیوی ریاضی) یک ماشین‌حساب دقیق است. ریاضی را عادی بنویسید: x^2، 2x، sin(x)/x، sqrt(2)، pi، e و oo برای بی‌نهایت — یا لاتک مثل \\frac{x^2-1}{x-1} را بچسبانید. بگویید چه کنم: ساده‌سازی، بسط، تجزیه، مشتق، انتگرال (برای نامعین حدها را خالی بگذارید)، حد، سری تیلور، مجموع، معادله و دستگاه (هر خط یکی)، معادلهٔ دیفرانسیل (بنویسید y'' + y = 0)، ماتریس (دترمینان، وارون، مقادیر ویژه…) و نمودار. هر پاسخ به‌صورت فرمول نشان داده می‌شود و می‌توان آن را به‌صورت لاتک کپی یا در صفحهٔ لاتک درج کرد. مسئلهٔ سخت بعد از ۹۰ ثانیه متوقف می‌شود.

غلط‌یاب در صفحهٔ لاتک واژه‌های غلط انگلیسی و فارسی را با موج قرمز خط می‌کشد؛ دستورها، فرمول‌ها، برچسب‌ها و توضیحات نادیده گرفته می‌شوند. روی واژه راست‌کلیک کنید تا پیشنهاد، «افزودن به فرهنگ» یا «نادیده گرفتن» را ببینید. کادر تیک زیر ویرایشگر آن را خاموش می‌کند. نام رایج ریاضی‌دانان (باناخ، هیلبرت، فوریه…) از قبل شناخته‌شده است."""),
    ("افزونه‌ها و پنجره‌های جدا", """
در تنظیمات بخش «افزونه‌ها» هست. افزونه‌ها دانلودهای اختیاری‌اند که روی رایانهٔ شما می‌مانند و بعد از آن بدون اینترنت کار می‌کنند: «OCR فرمول» (تصویر یک فرمول چاپی را به لاتک تبدیل می‌کند؛ نتیجه را همیشه بررسی کنید — ممکن است نمادهایی مثل n و π را اشتباه بگیرد) و «بسته‌های بیشتر لاتک» (صدها بسته، کلاس و قلم بیشتر که بدون اینترنت کامپایل می‌شوند). نصب یا حذف با یک کلیک؛ فقط برای دانلود اینترنت لازم است.

یک نصب سه برنامه در منوی شروع می‌دهد: جعبه‌ابزار PDF (همه‌چیز)، مطالعه (فقط خواننده با نوار کناری باریک) و استودیوی ریاضی (ریاضی، فرمول از روی تصویر، لاتک و فرمول). فایل‌های مشترک دارند و فضای اضافه نمی‌خواهند. در نسخهٔ قابل‌حمل از Reader.bat و MathStudio.bat استفاده کنید. هنگام نصب می‌توانید «مطالعه» را به فهرست «باز کردن با» فایل‌های DjVu، EPUB، MOBI، FB2، CBZ و XPS اضافه کنید.

«پاک‌سازی اسکن» صفحه‌های کج را صاف می‌کند، سایه و نویز را برمی‌دارد و می‌تواند صفحه‌های سیاه‌وسفید کم‌حجم بسازد؛ بعد از آن OCR بزنید. «تعمیر و بهینه‌سازی» PDF آسیب‌دیده‌ای را که باز نمی‌شود بازسازی می‌کند."""),
    ("تم، تصویر و زبان", """
«تنظیمات» را باز کنید. روی یک تم رنگی بزنید تا فوراً اعمال شود؛ تم روشن و تیره دارید.

تصویر پشت کل پنجره را می‌توانید عوض کنید: یک سبک (شفق، موج، کوه…) انتخاب کنید یا با «انتخاب تصویر من…» عکس خودتان را بگذارید. گزینهٔ «متوسط / پررنگ» تعیین می‌کند چه مقدار از تصویر از میان کارت‌ها دیده شود.

زبان: English یا فارسی را انتخاب کنید. برای تغییر زبان برنامه دوباره باز می‌شود و رابط فارسی راست‌به‌چپ چیده می‌شود."""),
    ("لاتک و فرمول‌ها", """
صفحهٔ «لاتک» را باز کنید تا فایل tex بنویسید یا باز کنید. «کامپایل» (یا Ctrl+Enter) را بزنید: PDF سمت راست نمایش داده می‌شود و هر خطا همراه با شمارهٔ خط و یک راهنمای ساده پایین فهرست می‌شود. روی خطا بزنید تا به همان خط بروید.

«جدید از قالب» سندهای آماده می‌دهد: مقاله با قضیه، پایان‌نامه، اسلاید (Beamer)، مقالهٔ فارسی + انگلیسی و یادداشت‌های شیمی و فیزیک.

«درون‌ریزی» فایل ورد، ODT، Markdown، EPUB یا HTML را به فایل tex تبدیل می‌کند و معادله‌ها به‌صورت لاتک می‌مانند.

«تبدیل به PDF» حالا معادله‌ها را در فایل‌های ورد، Markdown، ODT و EPUB درست حروف‌چینی می‌کند، حتی داخل سندهای فارسی. فایل tex را هم می‌توان مستقیم تبدیل کرد.

اولین کامپایل ممکن است برای گرفتن یک بسته به اینترنت نیاز داشته باشد؛ بعد از آن برای استفادهٔ آفلاین ذخیره می‌شود."""),
    ("نمادها، شیمی و فیزیک", """
«نمادها» را بزنید تا پالت باز شود: بیش از ۳۰۰ نماد در گروه‌ها (حروف یونانی، عملگرها، رابطه‌ها، پیکان‌ها، مجموعه و منطق، آنالیز، جبر، هندسه، قالب‌ها، فیزیک، شیمی، یکاها). روی یک نماد بزنید تا لاتک آن در جای مکان‌نما در ویرایشگر یا کادر فرمول درج شود. با راست‌کلیک فقط کپی می‌شود. با کادر جست‌وجو نماد را از روی نامش پیدا کنید، مثلاً integral، alpha یا norm.

گروه «آنالیز» نمادگذاری فضاهای تابعی و نرم‌ها، مشتق، انتگرال، همامیخت و تبدیل فوریه را دارد.

شیمی: واکنش‌ها را با \\ce{2H2 + O2 -> 2H2O}، یون‌ها را با \\ce{Fe^{3+}} و ساختارها را با \\chemfig{*6(=-=-=-)} بنویسید. فیزیک: یکاها با \\SI{9.81}{m/s^2} و براکت‌ها و مشتق‌ها با بستهٔ physics.

صفحهٔ «فرمول» یک فرمول را با زمینهٔ شفاف و رنگ دلخواه به PNG، SVG یا PDF تبدیل می‌کند؛ برای اسلاید تیره رنگ سفید را بزنید."""),
    ("پرسش‌ها و مشکل‌ها", """
برنامه کند است؟ فایل‌های بزرگ را در برنامه‌های دیگر ببندید. کارهای طولانی مثل OCR یک کتاب کامل در پس‌زمینه و با همهٔ هسته‌های پردازنده اجرا می‌شوند و پنجره در این مدت پاسخگو می‌ماند.

OCR چیزی پیدا نکرد؟ زبان را بررسی کنید و ۴۰۰ dpi را امتحان کنید. اسکن‌های خیلی تیره یا تار به عکس بهتری نیاز دارند.

پیام «رمزدار است»: PDF رمز دارد. ابتدا رمز را با برنامه‌ای که ساخته برداشید.

ویندوز می‌گوید برنامه ناشناس است: برنامه امضای دیجیتال ندارد. «More info» و سپس «Run anyway» را بزنید.

تنظیمات شما در پوشهٔ %APPDATA%\\PDFToolkit ذخیره می‌شود."""),
    ("دربارهٔ برنامه و مجوزها", """
جعبه‌ابزار PDF از این برنامه‌های رایگان استفاده می‌کند که هر کدام جدا و بدون تغییر اجرا می‌شوند: PyMuPDF (خواندن و صفحه‌آرایی)، Tesseract (OCR)، Ghostscript (فشرده‌سازی)، DjVuLibre (DjVu) و Pandoc (ورد/ODT/RTF/EPUB).

قلم‌ها: Noto Sans Arabic (مجوز SIL Open Font) و DejaVu Sans. متن کامل مجوزها در پوشهٔ fonts و فایل README پروژه است."""),
    ("ظاهر، تنظیمات و جست‌وجوی Ctrl+K", """
در هر جای برنامه Ctrl+K را بزنید تا کادر جست‌وجو باز شود. چند حرف از نام یک ابزار (مثلاً «واترمارک» یا «ادغام»)، یک تنظیم (مثلاً «تیره») یا نام کتابی که پیش‌تر باز کرده‌اید بنویسید و Enter بزنید.

تنظیمات > ظاهر: حالت روشن، تیره یا هم‌رنگ با ویندوز؛ سبک طراحی (آرام و حرفه‌ای تخت و ساده است، کاغذ گرم و شبیه کتاب است و کلاسیک پس‌زمینه‌های تصویری را نگه می‌دارد)؛ رنگ تأکید برای دکمه‌ها و پیوندها؛ هر کدام از ۱۳ تم رنگی؛ یکی از چهار سبک آیکن؛ اندازهٔ متن و قلم فارسی.

سه برنامه (جعبه‌ابزار PDF، خواننده و ریاضی‌استودیو) آیکن‌های تک‌رنگ دارند: نیلی، سبزآبی و سرخابی.

تنظیمات > فضای ذخیره نشان می‌دهد حافظهٔ نهانی خواننده و بسته‌های LaTeX چقدر جا می‌گیرند و آن‌ها را پاک می‌کند. به فایل‌های شما دست نمی‌زند.
"""),
]

TOPICS = {"en": EN, "fa": FA}
