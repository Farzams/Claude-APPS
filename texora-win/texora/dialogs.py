"""The small windows of the editor: outline, history, project check, insert tools, CSV, DOI, citation style, snippets."""
import threading
import time

from .qt import Qt, QtCore, QtGui, QtWidgets, Signal, QObject, run_dialog
from . import csvtool, doi as doi_mod
from .strings import t


def _buttons(dlg, ok_text=None, cancel=True, on_ok=None):
    box = QtWidgets.QHBoxLayout()
    box.addStretch(1)
    if cancel:
        c = QtWidgets.QPushButton(t("cancel"))
        c.clicked.connect(dlg.reject)
        box.addWidget(c)
    ok = QtWidgets.QPushButton(ok_text or t("ok.button"))
    ok.setObjectName("primary")
    ok.setDefault(True)
    ok.clicked.connect(on_ok or dlg.accept)
    box.addWidget(ok)
    return box, ok


class _Base(QtWidgets.QDialog):
    def __init__(self, parent, title, width=460):
        super(_Base, self).__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        self.lay = QtWidgets.QVBoxLayout(self)
        self.lay.setContentsMargins(20, 18, 20, 16)
        self.lay.setSpacing(12)
        h = QtWidgets.QLabel(title)
        h.setObjectName("h2")
        self.lay.addWidget(h)


class OutlineDialog(_Base):
    def __init__(self, parent, items, stats, on_go):
        super(OutlineDialog, self).__init__(parent, t("outline"), 480)
        self.on_go = on_go
        for s in stats:
            lab = QtWidgets.QLabel(s)
            lab.setObjectName("muted")
            self.lay.addWidget(lab)
        self.list = QtWidgets.QListWidget()
        self.list.setMinimumHeight(260)
        if not items:
            self.list.addItem(t("outline.none"))
        for it in items:
            li = QtWidgets.QListWidgetItem(("      " * it.level) + (it.title or "·"))
            li.setData(Qt.UserRole, it.line)
            f = li.font()
            f.setBold(it.level == 0)
            li.setFont(f)
            self.list.addItem(li)
        self.list.itemActivated.connect(self._go)
        self.list.itemClicked.connect(self._go)
        self.lay.addWidget(self.list)
        box, _ = _buttons(self, cancel=False)
        self.lay.addLayout(box)

    def _go(self, item):
        line = item.data(Qt.UserRole)
        if line:
            self.on_go(line)
            self.accept()


class HistoryDialog(_Base):
    def __init__(self, parent, versions, read, on_restore):
        super(HistoryDialog, self).__init__(parent, t("history"), 480)
        self.versions, self.read, self.on_restore = versions, read, on_restore
        lab = QtWidgets.QLabel(t("history.restore") if versions else t("history.none"))
        lab.setWordWrap(True)
        lab.setObjectName("muted")
        self.lay.addWidget(lab)
        self.list = QtWidgets.QListWidget()
        self.list.setMinimumHeight(240)
        for i, v in enumerate(versions):
            when = time.strftime("%Y-%m-%d  %H:%M", time.localtime(v[0] / 1000.0))
            n = len(read(v).split("\n"))
            li = QtWidgets.QListWidgetItem("%s    ·    %d %s" % (when, n, t("lines")))
            li.setData(Qt.UserRole, i)
            self.list.addItem(li)
        self.list.itemActivated.connect(self._restore)
        self.list.itemDoubleClicked.connect(self._restore)
        self.lay.addWidget(self.list)
        box, _ = _buttons(self, cancel=False)
        self.lay.addLayout(box)

    def _restore(self, item):
        self.on_restore(self.versions[item.data(Qt.UserRole)])
        self.accept()


class CheckDialog(_Base):
    def __init__(self, parent, issues, on_go):
        super(CheckDialog, self).__init__(parent, t("tool.check"), 560)
        self.on_go = on_go
        self.summary = QtWidgets.QLabel(t("check.none") if not issues else "%d %s" % (len(issues), t("check.found")))
        self.summary.setObjectName("h2" if issues else "muted")
        self.lay.addWidget(self.summary)
        self.list = QtWidgets.QListWidget()
        self.list.setMinimumHeight(260)
        for iss in issues:
            where = (iss.file or "") + (":%d" % iss.line if iss.line else "")
            li = QtWidgets.QListWidgetItem("%s\n%s    %s" % (t(iss.kind), iss.detail, where))
            li.setData(Qt.UserRole, (iss.file, iss.line))
            self.list.addItem(li)
        self.list.itemActivated.connect(self._go)
        self.list.itemClicked.connect(self._go)
        self.lay.addWidget(self.list)
        box, _ = _buttons(self, cancel=False)
        self.lay.addLayout(box)

    def _go(self, item):
        f, l = item.data(Qt.UserRole)
        self.on_go(f, l)
        self.accept()


class ToolsDialog(_Base):
    """Insert and check: five tools, one per row."""
    chosen = None

    def __init__(self, parent):
        super(ToolsDialog, self).__init__(parent, t("insert.tools"), 460)
        for key, name, hint in (("csv", "tool.csv", "tool.csv.d"), ("picture", "tool.picture", "tool.picture.d"),
                                ("doi", "tool.doi", "tool.doi.d"), ("style", "tool.style", "tool.style.d"),
                                ("check", "tool.check", "tool.check.d")):
            b = QtWidgets.QPushButton("%s\n%s" % (t(name), t(hint)))
            b.setStyleSheet("text-align: left; padding: 10px 14px;")
            b.clicked.connect(lambda _=False, k=key: self._pick(k))
            self.lay.addWidget(b)
        box, _ = _buttons(self, cancel=False, ok_text=t("cancel"))
        self.lay.addLayout(box)

    def _pick(self, key):
        self.chosen = key
        self.accept()


class CsvDialog(_Base):
    def __init__(self, parent, data):
        super(CsvDialog, self).__init__(parent, t("csv.title"), 480)
        self.data = data
        self.result_code = None
        self.needs_plot = False
        self.numeric = [i for i in range(len(data.header)) if data.is_numeric(i)]
        info = QtWidgets.QLabel("%d %s · %d %s" % (len(data.rows), t("csv.rows"), len(data.header), t("csv.cols")))
        info.setObjectName("muted")
        self.lay.addWidget(info)
        row = QtWidgets.QHBoxLayout()
        self.mode = "table"
        self.mode_buttons = {}
        can_plot = len(self.numeric) >= 2
        for key, name in (("table", "csv.table"), ("line", "csv.line"), ("scatter", "csv.scatter")):
            b = QtWidgets.QPushButton(t(name))
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(key == "table")
            b.setEnabled(key == "table" or can_plot)
            b.clicked.connect(lambda _=False, k=key: self._mode(k))
            self.mode_buttons[key] = b
            row.addWidget(b)
        row.addStretch(1)
        self.lay.addLayout(row)
        if not can_plot:
            n = QtWidgets.QLabel(t("csv.noplot"))
            n.setObjectName("muted")
            self.lay.addWidget(n)
        self.axis = QtWidgets.QWidget()
        al = QtWidgets.QVBoxLayout(self.axis)
        al.setContentsMargins(0, 0, 0, 0)
        al.addWidget(QtWidgets.QLabel(t("csv.x")))
        self.x_combo = QtWidgets.QComboBox()
        for i in self.numeric:
            self.x_combo.addItem(data.header[i], i)
        self.x_combo.currentIndexChanged.connect(self._x_changed)
        al.addWidget(self.x_combo)
        al.addWidget(QtWidgets.QLabel(t("csv.y")))
        self.y_list = QtWidgets.QListWidget()
        self.y_list.setMaximumHeight(110)
        al.addWidget(self.y_list)
        self.lay.addWidget(self.axis)
        self._x_changed()
        self.axis.hide()
        self.caption = QtWidgets.QLineEdit()
        self.caption.setPlaceholderText(t("csv.caption"))
        self.lay.addWidget(self.caption)
        box, ok = _buttons(self, t("csv.insert"), on_ok=self._insert)
        self.lay.addLayout(box)

    def _mode(self, key):
        self.mode = key
        for k, b in self.mode_buttons.items():
            b.setChecked(k == key)
        self.axis.setVisible(key != "table")
        self.adjustSize()

    def _x_changed(self, *_):
        x = self.x_combo.currentData()
        self.y_list.clear()
        first = True
        for i in self.numeric:
            if i == x:
                continue
            li = QtWidgets.QListWidgetItem(self.data.header[i])
            li.setFlags(li.flags() | Qt.ItemIsUserCheckable)
            li.setCheckState(Qt.Checked if first else Qt.Unchecked)
            li.setData(Qt.UserRole, i)
            self.y_list.addItem(li)
            first = False

    def _insert(self):
        cap = self.caption.text()
        if self.mode == "table":
            self.result_code, self.needs_plot = csvtool.table(self.data, cap), False
        else:
            ys = [self.y_list.item(k).data(Qt.UserRole) for k in range(self.y_list.count())
                  if self.y_list.item(k).checkState() == Qt.Checked]
            if not ys and self.y_list.count():
                ys = [self.y_list.item(0).data(Qt.UserRole)]
            self.result_code = csvtool.plot(self.data, self.x_combo.currentData(), ys, cap, self.mode == "scatter")
            self.needs_plot = True
        self.accept()


class _Fetcher(QObject):
    done = Signal(object, object)


class DoiDialog(_Base):
    def __init__(self, parent):
        super(DoiDialog, self).__init__(parent, t("tool.doi"), 480)
        self.entry = None
        self.field = QtWidgets.QLineEdit()
        self.field.setPlaceholderText("10.1000/xyz123")
        self.lay.addWidget(self.field)
        n = QtWidgets.QLabel(t("doi.online"))
        n.setWordWrap(True)
        n.setObjectName("muted")
        self.lay.addWidget(n)
        self.err = QtWidgets.QLabel("")
        self.err.setWordWrap(True)
        self.err.setStyleSheet("color: #DC2626;")
        self.lay.addWidget(self.err)
        self.bar = QtWidgets.QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.hide()
        self.lay.addWidget(self.bar)
        box, self.ok = _buttons(self, t("doi.add"), on_ok=self._go)
        self.lay.addLayout(box)
        self.fetcher = _Fetcher()
        self.fetcher.done.connect(self._result)

    def _go(self):
        d = doi_mod.clean(self.field.text())
        if d is None:
            self.err.setText(t("doi.bad"))
            return
        self.err.setText("")
        self.ok.setEnabled(False)
        self.bar.show()

        def work():
            entry, error = doi_mod.fetch(d)
            self.fetcher.done.emit(entry, error)
        threading.Thread(target=work, daemon=True).start()

    def _result(self, entry, error):
        self.bar.hide()
        self.ok.setEnabled(True)
        if entry:
            self.entry = entry
            self.accept()
        else:
            self.err.setText(t("doi.fail"))


class StyleDialog(_Base):
    chosen = None

    def __init__(self, parent):
        super(StyleDialog, self).__init__(parent, t("tool.style"), 420)
        hint = QtWidgets.QLabel(t("style.hint"))
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        self.lay.addWidget(hint)
        for sid, key in (("plain", "style.plain"), ("unsrt", "style.unsrt"), ("alpha", "style.alpha"), ("abbrv", "style.abbrv")):
            b = QtWidgets.QPushButton(t(key))
            b.setStyleSheet("text-align: left; padding: 9px 14px;")
            b.clicked.connect(lambda _=False, s=sid: self._pick(s))
            self.lay.addWidget(b)
        box, _ = _buttons(self, cancel=False, ok_text=t("cancel"))
        self.lay.addLayout(box)

    def _pick(self, s):
        self.chosen = s
        self.accept()


class SnippetDialog(_Base):
    def __init__(self, parent, text=""):
        super(SnippetDialog, self).__init__(parent, t("snippet.save"), 480)
        self.label = QtWidgets.QLineEdit()
        self.label.setPlaceholderText(t("snippet.label"))
        self.lay.addWidget(self.label)
        hint = QtWidgets.QLabel(t("snippet.text"))
        hint.setObjectName("muted")
        self.lay.addWidget(hint)
        self.body = QtWidgets.QPlainTextEdit(text)
        self.body.setMinimumHeight(110)
        f = QtGui.QFont("Consolas")
        f.setStyleHint(QtGui.QFont.Monospace)
        self.body.setFont(f)
        self.lay.addWidget(self.body)
        box, _ = _buttons(self)
        self.lay.addLayout(box)


class ViewDialog(_Base):
    def __init__(self, parent, size, numbers, wrap, pairs, bar):
        super(ViewDialog, self).__init__(parent, t("view.options"), 380)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(t("font.size")))
        self.size = QtWidgets.QSpinBox()
        self.size.setRange(8, 28)
        self.size.setValue(size)
        row.addWidget(self.size)
        row.addStretch(1)
        self.lay.addLayout(row)
        self.numbers = QtWidgets.QCheckBox(t("line.numbers"))
        self.numbers.setChecked(numbers)
        self.wrap = QtWidgets.QCheckBox(t("wrap"))
        self.wrap.setChecked(wrap)
        self.pairs = QtWidgets.QCheckBox(t("auto.pairs"))
        self.pairs.setChecked(pairs)
        self.bar = QtWidgets.QCheckBox(t("palette"))
        self.bar.setChecked(bar)
        for w in (self.numbers, self.wrap, self.pairs, self.bar):
            self.lay.addWidget(w)
        box, _ = _buttons(self)
        self.lay.addLayout(box)


def ask_text(parent, title, label, value=""):
    text, ok = QtWidgets.QInputDialog.getText(parent, title, label, QtWidgets.QLineEdit.Normal, value)
    return text.strip() if ok else None


def confirm(parent, text):
    return QtWidgets.QMessageBox.question(parent, "TeXora", text) == QtWidgets.QMessageBox.Yes
