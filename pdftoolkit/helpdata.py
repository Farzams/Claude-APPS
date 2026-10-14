"""Help topics in English and Persian: {lang: [(title, body), ...]}. Paragraphs are separated by a blank line."""

EN = [
    ('Getting started', """
PDF Toolkit does the everyday jobs with PDFs in one place: OCR, convert, split, merge, compress, turn pictures into PDFs and edit pages.

Pick a tool from the list on the side, or click one of the cards on the Home page. Press Ctrl+K to search every tool. Choose your file with Browse… or simply drag it onto the window.

Long jobs show a progress bar at the bottom. When a job finishes, the log tells you what happened and Open folder takes you to the result.

Everything is built in. Nothing else needs to be installed.
"""),
    ('OCR: scanned books', """
OCR adds an invisible text layer to scanned pages so you can search and copy them. The pictures of the pages are not changed.

Choose the language of the book (Persian is the first choice). Keep "Also recognise English words" ticked when the text mixes Persian and English, for example formulas, names and references.

Scan quality: 300 dpi is the best choice for normal books. Use 400 dpi for very small print and 200 dpi for a quick draft.

Pages that already contain text are skipped unless you untick the option. OCR of a long book can take a few minutes; the app uses all processor cores.

Tips for better results: straight, sharp, dark-on-light scans work best. Photos taken at an angle or with shadows reduce accuracy."""),
    ('Persian (Farsi) tips', """
Searching and copying work on PDFs that contain real text, or after you run OCR on scans.

Converting: EPUB, FB2, TXT and HTML files that contain Persian are shaped (letters joined) and laid out right-to-left automatically. Headings become bookmarks.

Old text files: files saved in Windows-1256 or UTF-16 are read correctly.

Interface: Settings > General switches the app to Persian; Settings > Appearance lets you pick the Persian font.
"""),
    ('Convert to PDF', """
Add one or more files, choose the output folder and press Convert.

Works without extra software: EPUB, MOBI, FB2, XPS, CBZ, HTML, TXT, DjVu, LaTeX (.tex) and common picture formats.

For ebooks you can choose page size and font size. A5 with size 11 is comfortable on a tablet.

Word, ODT, RTF and Markdown files are not supported. Only very old formats (.doc, .lit, .pdb, .cbr) need the free program Calibre; the app tells you if that is the case.
"""),
    ('Split, Merge and Page tools', """
Split: cut a PDF by ranges (1-3, 5, 8- makes three files), every N pages, into N equal parts or one file per page.

Merge: add the PDFs, put them in order with ▲ ▼ and choose where to save.

Page tools: delete pages, keep only some pages, rotate pages or reverse the order. Page lists work like in the Split tool: 1-3, 7, 10-.

The original file is never changed; the result is saved as a new file."""),
    ('Compress', """
Four levels: Low keeps full quality and only tidies the file; Medium (150 dpi pictures) is good for most uses; High (110 dpi) and Extreme (72 dpi) give the smallest files.

The Ghostscript engine is strongest for scanned books. If a file cannot be made smaller, the original is kept so you never get a bigger file.

The result is saved as name_compressed.pdf next to your choice of folder."""),
    ('Images to PDF', """
Add many pictures, reorder them with ▲ ▼ and choose the page size: A4, A5, Letter or Fit to image (each page takes the size of its picture).

Photos from a phone are rotated correctly. Transparent PNG pictures get a white background.

Combine this with OCR to turn photos of book pages into a searchable PDF."""),
    ('PDF tools: organize, edit, protect', """
All tools are listed in All tools (type to search).

Organize pages: drag the thumbnails to reorder; rotate, delete, duplicate, extract or insert pages from another PDF or picture; Undo goes back step by step. Crop pages trims white margins automatically or cuts a fixed margin. Delete blank pages finds empty pages, also nearly-white scans.

Edit PDF: replace text (Persian works), add text or a picture inside a box you draw, replace or remove a picture. Header, footer & Bates adds page numbers, dates, file names and Bates numbers. Watermark stamps text or a picture at any angle. Page background paints a colour or picture behind the content.

PDF to…: pictures (PNG, JPEG, TIFF), Word, Excel (tables), HTML or text. The Word export keeps text, pictures and right-to-left direction but simplifies the exact layout. Scanned PDFs: tick the OCR option first.

Password & permissions: protects with AES-256 and can forbid printing, copying or editing. A forgotten password cannot be recovered. Remove hidden data cleans author names, comments, attachments and scripts. Redact black out words, patterns (e-mail, phone, card numbers) or drawn areas — the text under the black is deleted for good.

Compare PDFs shows what changed, as text and as a picture with differences in red. Batch process runs one operation on a whole list of files."""),
    ('Look, Settings and Ctrl+K search', """
Press Ctrl+K anywhere to open the search box. Type a few letters of a tool ("water", "merge") or a setting ("dark", "icons"), then press Enter.

Settings > Appearance: choose Light, Dark or Match Windows; a design style (Quiet Pro is flat and calm, Paper is warm like a book, Classic is the original look); an accent colour for buttons and links; any of the 13 colour themes; one of four icon styles; the text size; and the Persian font.

Language: Settings > General switches between English and فارسی. The app restarts to switch language; the Persian interface is laid out right-to-left.

Settings > Storage shows how much space the LaTeX package cache uses and clears it. Nothing you save is touched.
"""),
    ('Questions and problems', """
The app feels slow? Close big files in other programs. Long jobs such as OCR of a whole book run in the background and use all processor cores; the window stays responsive while they work.

OCR found nothing? Check the language and try 400 dpi. Very dark or blurry scans need better photos.

"Password protected" message: the PDF is encrypted. Remove the password with the program that created it first.

Windows says the app is unknown: it is not digitally signed. Choose More info, then Run anyway.

Your settings are stored in the folder %APPDATA%\\PDFToolkit."""),
    ('About and licences', """
PDF Toolkit uses these free programs, each running separately and unmodified: PyMuPDF (reading, layout), Tesseract (OCR), Ghostscript (compression), DjVuLibre (DjVu), Tectonic (LaTeX files).

Fonts: Inter, Vazirmatn, Noto Sans Arabic (SIL Open Font License) and DejaVu Sans. Full licence texts are in the fonts folder and in the project README.
"""),
]

FA = [
    ('شروع کار', """
جعبه‌ابزار PDF کارهای روزمرهٔ PDF را یک‌جا انجام می‌دهد: OCR، تبدیل، جداسازی، ادغام، فشرده‌سازی، ساخت PDF از تصویر و ویرایش صفحه‌ها.

یکی از ابزارها را از فهرست کناری انتخاب کنید یا روی یکی از کارت‌های صفحهٔ خانه بزنید. با Ctrl+K در همهٔ ابزارها جست‌وجو کنید. فایل را با «مرور…» انتخاب کنید یا فقط روی پنجره بکشید و رها کنید.

در کارهای طولانی نوار پیشرفت پایین صفحه نمایش داده می‌شود. پس از پایان، گزارش نتیجه را می‌بینید و با «باز کردن پوشه» به فایل خروجی می‌رسید.

همه‌چیز داخل برنامه است و به نصب چیز دیگری نیاز ندارید.
"""),
    ('OCR: کتاب\u200cهای اسکن\u200cشده', """
OCR یک لایهٔ نامرئی متن به صفحه‌های اسکن‌شده می‌افزاید تا بتوانید در آن‌ها جست‌وجو و از آن‌ها کپی کنید. تصویر صفحه‌ها تغییر نمی‌کند.

زبان کتاب را انتخاب کنید (فارسی گزینهٔ اول است). وقتی متن فارسی و انگلیسی با هم است، مثل فرمول‌ها، نام‌ها و منابع، گزینهٔ «کلمه‌های انگلیسی را هم بشناس» را روشن نگه دارید.

کیفیت اسکن: برای کتاب‌های معمولی ۳۰۰ dpi بهترین انتخاب است. برای چاپ بسیار ریز ۴۰۰ و برای پیش‌نویس سریع ۲۰۰ را بزنید.

صفحه‌هایی که از قبل متن دارند رد می‌شوند، مگر این گزینه را خاموش کنید. OCR یک کتاب بلند چند دقیقه طول می‌کشد؛ برنامه از همهٔ هسته‌های پردازنده استفاده می‌کند.

برای نتیجهٔ بهتر: اسکن صاف، واضح و با نوشتهٔ تیره روی زمینهٔ روشن بهترین است. عکس کج یا همراه با سایه دقت را کم می‌کند."""),
    ('نکته\u200cهایی برای فارسی', """
جست‌وجو و کپی در PDFهایی کار می‌کند که متن واقعی دارند، یا بعد از اجرای OCR روی اسکن‌ها.

تبدیل: فایل‌های EPUB، FB2، TXT و HTML که فارسی دارند خودکار حرف‌به‌حرف به هم چسبیده و راست‌به‌چپ چیده می‌شوند. عنوان‌ها به نشانک (bookmark) تبدیل می‌شوند.

فایل‌های قدیمی: فایل‌های متنی با کدگذاری Windows-1256 یا UTF-16 درست خوانده می‌شوند.

رابط: «تنظیمات > عمومی» برنامه را فارسی می‌کند و «تنظیمات > ظاهر» اجازهٔ انتخاب قلم فارسی را می‌دهد.
"""),
    ('تبدیل به PDF', """
یک یا چند فایل را اضافه کنید، پوشهٔ خروجی را انتخاب کنید و «تبدیل» را بزنید.

بدون نرم‌افزار اضافه کار می‌کند: EPUB، MOBI، FB2، XPS، CBZ، HTML، TXT، DjVu، لاتک (tex) و قالب‌های رایج تصویر.

برای کتاب‌های الکترونیکی می‌توانید اندازهٔ صفحه و اندازهٔ قلم را انتخاب کنید. A5 با اندازهٔ ۱۱ برای تبلت راحت است.

فایل‌های ورد، ODT، RTF و Markdown پشتیبانی نمی‌شوند. فقط قالب‌های خیلی قدیمی (doc، lit، pdb، cbr) به برنامهٔ رایگان Calibre نیاز دارند و برنامه در این مورد به شما خبر می‌دهد.
"""),
    ('جداسازی، ادغام و ابزار صفحات', """
جداسازی: PDF را با بازه (۱-۳، ۵، ۸- سه فایل می‌سازد)، هر N صفحه، به N بخش مساوی یا هر صفحه در یک فایل می‌برد.

ادغام: PDFها را اضافه کنید، با ▲ ▼ ترتیبشان را بدهید و محل ذخیره را انتخاب کنید.

ابزار صفحات: حذف صفحه، نگه‌داشتن چند صفحه، چرخاندن صفحه یا وارونه کردن ترتیب. فهرست صفحه‌ها مثل ابزار جداسازی نوشته می‌شود: 1-3, 7, 10-

فایل اصلی هرگز تغییر نمی‌کند و نتیجه در فایل تازه‌ای ذخیره می‌شود."""),
    ('فشرده\u200cسازی', """
چهار سطح دارد: «کم» کیفیت را کامل نگه می‌دارد و فقط فایل را مرتب می‌کند؛ «متوسط» (تصویر ۱۵۰ dpi) برای بیشتر کارها خوب است؛ «زیاد» (۱۱۰ dpi) و «بیشترین» (۷۲ dpi) کوچک‌ترین فایل را می‌دهند.

موتور Ghostscript برای کتاب‌های اسکن‌شده قوی‌ترین است. اگر فایل کوچک‌تر نشود، فایل اصلی نگه داشته می‌شود تا هرگز فایل بزرگ‌تر نگیرید.

نتیجه با نام name_compressed.pdf در پوشه‌ای که انتخاب کرده‌اید ذخیره می‌شود."""),
    ('تصویر به PDF', """
چندین تصویر را اضافه کنید، با ▲ ▼ ترتیب بدهید و اندازهٔ صفحه را انتخاب کنید: A4، A5، Letter یا «هم‌اندازهٔ تصویر» (هر صفحه به اندازهٔ تصویرش می‌شود).

عکس‌های موبایل درست چرخانده می‌شوند و تصویرهای PNG شفاف زمینهٔ سفید می‌گیرند.

با OCR ترکیبش کنید تا عکس صفحه‌های کتاب به PDF قابل جست‌وجو تبدیل شود."""),
    ('ابزارهای PDF: مرتب\u200cسازی، ویرایش، حفاظت', """
همهٔ ابزارها در «همهٔ ابزارها» فهرست شده‌اند (برای جست‌وجو تایپ کنید).

مرتب‌سازی صفحه‌ها: تصویرهای بندانگشتی را بکشید تا جابه‌جا شوند؛ بچرخانید، حذف، تکثیر، استخراج یا از PDF و تصویر دیگر درج کنید؛ «واگرد» قدم‌به‌قدم برمی‌گردد. برش صفحه‌ها حاشیهٔ سفید را خودکار می‌برد یا حاشیهٔ ثابتی را. حذف صفحه‌های خالی صفحه‌های خالی و اسکن‌های تقریباً سفید را پیدا می‌کند.

ویرایش PDF: جایگزینی متن (فارسی هم کار می‌کند)، افزودن متن یا تصویر داخل جعبه‌ای که می‌کشید، تعویض یا حذف تصویر. سرصفحه، پاصفحه و باتس شمارهٔ صفحه، تاریخ، نام فایل و شمارهٔ باتس می‌افزاید. واترمارک متن یا تصویر را با هر زاویه می‌زند. پس‌زمینهٔ صفحه رنگ یا تصویری پشت محتوا می‌گذارد.

PDF به…: تصویر (PNG، JPEG، TIFF)، ورد، اکسل (جدول‌ها)، HTML یا متن. خروجی ورد متن، تصویر و جهت راست‌به‌چپ را نگه می‌دارد ولی چیدمان دقیق را ساده می‌کند. برای PDF اسکن‌شده اول گزینهٔ OCR را تیک بزنید.

گذرواژه و دسترسی‌ها: با AES-256 محافظت می‌کند و می‌تواند چاپ، کپی یا ویرایش را ممنوع کند. گذرواژهٔ فراموش‌شده بازیابی نمی‌شود. حذف داده‌های پنهان نام نویسنده، نظرها، پیوست‌ها و اسکریپت‌ها را پاک می‌کند. سانسور واژه‌ها، الگوها (ایمیل، تلفن، کارت) یا ناحیه‌های کشیده‌شده را می‌پوشاند — متن زیر نوار سیاه برای همیشه پاک می‌شود.

مقایسهٔ PDFها نشان می‌دهد چه چیزی تغییر کرده، هم متنی و هم تصویری با تفاوت‌های قرمز. پردازش دسته‌ای یک عملیات را روی فهرستی از فایل‌ها اجرا می‌کند."""),
    ('ظاهر، تنظیمات و جست\u200cوجوی Ctrl+K', """
در هر جای برنامه Ctrl+K را بزنید تا کادر جست‌وجو باز شود. چند حرف از نام یک ابزار (مثلاً «واترمارک» یا «ادغام») یا یک تنظیم (مثلاً «تیره») بنویسید و Enter بزنید.

تنظیمات > ظاهر: حالت روشن، تیره یا هم‌رنگ با ویندوز؛ سبک طراحی (آرام و حرفه‌ای تخت و ساده است، کاغذ گرم و شبیه کتاب است و کلاسیک همان ظاهر اولیه است)؛ رنگ تأکید برای دکمه‌ها و پیوندها؛ هر کدام از ۱۳ تم رنگی؛ یکی از چهار سبک آیکن؛ اندازهٔ متن و قلم فارسی.

زبان: «تنظیمات > عمومی» بین English و فارسی جابه‌جا می‌کند. برای تغییر زبان برنامه دوباره باز می‌شود و رابط فارسی راست‌به‌چپ چیده می‌شود.

تنظیمات > فضای ذخیره نشان می‌دهد حافظهٔ بسته‌های LaTeX چقدر جا می‌گیرد و آن را پاک می‌کند. به فایل‌های شما دست نمی‌زند.
"""),
    ('پرسش\u200cها و مشکل\u200cها', """
برنامه کند است؟ فایل‌های بزرگ را در برنامه‌های دیگر ببندید. کارهای طولانی مثل OCR یک کتاب کامل در پس‌زمینه و با همهٔ هسته‌های پردازنده اجرا می‌شوند و پنجره در این مدت پاسخگو می‌ماند.

OCR چیزی پیدا نکرد؟ زبان را بررسی کنید و ۴۰۰ dpi را امتحان کنید. اسکن‌های خیلی تیره یا تار به عکس بهتری نیاز دارند.

پیام «رمزدار است»: PDF رمز دارد. ابتدا رمز را با برنامه‌ای که ساخته برداشید.

ویندوز می‌گوید برنامه ناشناس است: برنامه امضای دیجیتال ندارد. «More info» و سپس «Run anyway» را بزنید.

تنظیمات شما در پوشهٔ %APPDATA%\\PDFToolkit ذخیره می‌شود."""),
    ('دربارهٔ برنامه و مجوزها', """
جعبه‌ابزار PDF از این برنامه‌های رایگان استفاده می‌کند که هر کدام جدا و بدون تغییر اجرا می‌شوند: PyMuPDF (خواندن و صفحه‌آرایی)، Tesseract (OCR)، Ghostscript (فشرده‌سازی)، DjVuLibre (DjVu) و Tectonic (فایل‌های لاتک).

قلم‌ها: Inter، Vazirmatn، Noto Sans Arabic (مجوز SIL Open Font) و DejaVu Sans. متن کامل مجوزها در پوشهٔ fonts و فایل README پروژه است.
"""),
]

TOPICS = {"en": EN, "fa": FA}
