"""The start page (projects), the new-project window and the settings page."""
import os
import time

from .qt import Qt, QtCore, QtGui, QtWidgets, Signal, QSize, run_dialog
from . import templates as tpl_mod
from . import theme as th
from . import __version__
from .dialogs import _Base, _buttons, ask_text, confirm
from .strings import t


class Header(QtWidgets.QWidget):
    """The title area of a start page; its look follows the theme: plain, centred with a rule, a coloured banner, small capitals."""

    def __init__(self, theme, title, subtitle, parent=None):
        super(Header, self).__init__(parent)
        self.theme = theme
        self.style = theme.spec["header"]
        self.setObjectName("header")
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(24, 18, 16, 14)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(2)
        banner = self.style in ("banner", "hero")
        self.title = QtWidgets.QLabel(title.upper() if self.style == "upper" else title)
        self.title.setObjectName("title")
        self.sub = QtWidgets.QLabel(subtitle.upper() if self.style == "upper" else subtitle)
        self.sub.setObjectName("muted")
        if banner:
            self.title.setStyleSheet("color: white; background: transparent;")
            self.sub.setStyleSheet("color: rgba(255,255,255,0.9); background: transparent;")
        if self.style == "center":
            self.title.setAlignment(Qt.AlignCenter)
            self.sub.setAlignment(Qt.AlignCenter)
        col.addWidget(self.title)
        col.addWidget(self.sub)
        lay.addLayout(col, 1)
        self.actions = QtWidgets.QHBoxLayout()
        self.actions.setSpacing(4)
        lay.addLayout(self.actions)

    def add_action(self, text, tip, fn):
        b = QtWidgets.QToolButton()
        b.setText(text)
        b.setToolTip(tip)
        b.setMinimumSize(36, 36)
        f = b.font()
        f.setPointSize(14)
        b.setFont(f)
        if self.style in ("banner", "hero"):
            b.setStyleSheet("QToolButton { color: white; } QToolButton:hover { background: rgba(255,255,255,0.2); }")
        b.clicked.connect(fn)
        self.actions.addWidget(b)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        acc = QtGui.QColor(self.theme.accent)
        r = QtCore.QRectF(self.rect()).adjusted(14, 8, -14, -6)
        if self.style in ("banner", "hero"):
            g = QtGui.QLinearGradient(r.topLeft(), r.bottomRight())
            if self.style == "hero":
                g.setColorAt(0, QtGui.QColor(th.lerp(self.theme.accent, "#FFFFFF", 0.22)))
                g.setColorAt(0.5, acc)
                g.setColorAt(1, QtGui.QColor(th.lerp(self.theme.accent, "#C2185B", 0.55)))
            else:
                g.setColorAt(0, acc)
                g.setColorAt(1, QtGui.QColor(th.lerp(self.theme.accent, "#FFFFFF", 0.2)))
            p.setBrush(QtGui.QBrush(g))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, self.theme.r_large, self.theme.r_large)
        elif self.style == "center":
            p.setPen(QtGui.QColor(th.lerp(self.theme.pal.line, self.theme.pal.text, 0.4)))
            p.drawLine(24, self.height() - 3, self.width() - 24, self.height() - 3)


class ProjectCard(QtWidgets.QFrame):
    opened = Signal(object)
    menu_action = Signal(str, object)

    def __init__(self, project, meta, theme, parent=None):
        super(ProjectCard, self).__init__(parent)
        self.project = project
        self.setObjectName("card")
        self.setCursor(Qt.PointingHandCursor)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 8, 12)
        glyph = QtWidgets.QLabel()
        glyph.setFixedSize(48, 62)
        pm = QtGui.QPixmap(48, 62)
        pm.fill(Qt.transparent)
        p = QtGui.QPainter(pm)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setBrush(QtGui.QColor("white"))
        p.setPen(QtGui.QPen(QtGui.QColor(theme.pal.line)))
        p.drawRoundedRect(1, 1, 46, 60, 6, 6)
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QColor(theme.accent))
        p.drawRoundedRect(8, 9, 26, 5, 2, 2)
        p.setBrush(QtGui.QColor("#D5D8E2"))
        for i in range(6):
            p.drawRoundedRect(8, 20 + i * 6, 32 if i < 5 else 20, 2, 1, 1)
        p.end()
        glyph.setPixmap(pm)
        lay.addWidget(glyph)
        col = QtWidgets.QVBoxLayout()
        col.setSpacing(3)
        name = QtWidgets.QLabel(project.name)
        name.setObjectName("h2")
        when = time.strftime("%Y-%m-%d", time.localtime(project.modified()))
        sub = QtWidgets.QLabel("%s   ·   %d %s   ·   %s" % (when, project.file_count(), t("files"),
                                                                      t("engine.xetex.short" if meta.engine == "xetex" else "engine.pdftex.short")))
        sub.setObjectName("muted")
        col.addWidget(name)
        col.addWidget(sub)
        lay.addLayout(col, 1)
        more = QtWidgets.QToolButton()
        more.setText("⋮")
        more.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        menu = QtWidgets.QMenu(more)
        for key, label in (("rename", "rename"), ("duplicate", "duplicate"), ("export", "export.zip"), ("delete", "delete")):
            if self.project.external and key in ("rename", "duplicate"):
                continue
            menu.addAction(t("a.remove.list") if (key == "delete" and self.project.external) else t(label),
                           lambda k=key: self.menu_action.emit(k, self.project))
        more.setMenu(menu)
        lay.addWidget(more)
        self.setMinimumHeight(86)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.opened.emit(self.project)
        super(ProjectCard, self).mousePressEvent(e)


class ProjectsPage(QtWidgets.QWidget):
    open_project = Signal(object)
    open_settings = Signal()

    def __init__(self, store, theme, prefs, parent=None):
        super(ProjectsPage, self).__init__(parent)
        self.store, self.theme, self.prefs = store, theme, prefs
        self.extras = lambda: []       # projects that live in other folders
        self.forget = None             # called to take such a project off the list
        self.setObjectName("page")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.header = Header(theme, t("app.latex"), t("latex.sub"))
        self.header.add_action("↓", t("import"), self.import_zip)
        self.header.add_action("⚙", t("settings"), self.open_settings.emit)
        outer.addWidget(self.header)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText(t("search.projects"))
        self.search.textChanged.connect(self.refresh)
        holder = QtWidgets.QWidget()
        hl = QtWidgets.QVBoxLayout(holder)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.addWidget(self.search)
        outer.addWidget(holder)
        self.area = QtWidgets.QScrollArea()
        self.area.setWidgetResizable(True)
        self.body = QtWidgets.QWidget()
        self.body.setObjectName("page")
        self.cards = QtWidgets.QVBoxLayout(self.body)
        self.cards.setContentsMargins(24, 12, 24, 90)
        self.cards.setSpacing(10)
        self.cards.setAlignment(Qt.AlignTop)
        self.area.setWidget(self.body)
        outer.addWidget(self.area, 1)
        self.fab = QtWidgets.QPushButton("+  " + t("new.project"), self)
        self.fab.setObjectName("primary")
        self.fab.setMinimumHeight(46)
        self.fab.clicked.connect(self.new_project)
        self.refresh()

    def resizeEvent(self, e):
        super(ProjectsPage, self).resizeEvent(e)
        self.fab.adjustSize()
        self.fab.move(self.width() - self.fab.width() - 28, self.height() - self.fab.height() - 24)

    def refresh(self, *_):
        while self.cards.count():
            w = self.cards.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        q = self.search.text().strip().lower()
        projects = [p for p in sorted(self.store.list() + list(self.extras()), key=lambda p: p.modified(), reverse=True) if q in p.name.lower()]
        if not projects:
            lab = QtWidgets.QLabel(t("no.projects"))
            lab.setObjectName("muted")
            lab.setWordWrap(True)
            self.cards.addWidget(lab)
        for p in projects:
            card = ProjectCard(p, self.store.meta(p), self.theme)
            card.opened.connect(self.open_project.emit)
            card.menu_action.connect(self._action)
            self.cards.addWidget(card)

    def new_project(self):
        d = NewProjectDialog(self)
        if run_dialog(d):
            p = self.store.create(d.name_text() or t(d.choice["key"]), d.choice)
            self.refresh()
            self.open_project.emit(p)

    def _action(self, key, project):
        if key == "rename":
            n = ask_text(self, t("rename"), t("project.name"), project.name)
            if n:
                self.store.rename(project, n)
        elif key == "duplicate":
            self.store.duplicate(project)
        elif key == "delete":
            if project.external:
                if confirm(self, "%s \"%s\"?" % (t("a.remove.list"), project.name)) and self.forget:
                    self.forget(project)
            elif confirm(self, "%s \"%s\"?" % (t("delete"), project.name)):
                self.store.delete(project)
        elif key == "export":
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, t("export.zip"), project.name + ".zip", "ZIP (*.zip)")
            if path:
                self.store.export_zip(project, path)
        self.refresh()

    def import_zip(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, t("import"), "", "ZIP / TeX (*.zip *.tex)")
        if not path:
            return
        if path.lower().endswith(".zip"):
            p = self.store.import_zip(os.path.basename(path), path)
        else:
            with open(path, "rb") as f:
                text = f.read().decode("utf-8", "replace")
            name = os.path.basename(path)
            p = self.store.create(name.rsplit(".", 1)[0], {"files": {name: text}, "main": name, "engine": "xetex"})
        self.refresh()
        self.open_project.emit(p)


class NewProjectDialog(_Base):
    def __init__(self, parent):
        super(NewProjectDialog, self).__init__(parent, t("new.project"), 480)
        self.all = tpl_mod.all_templates()
        self.choice = self.all[0]
        self.name = QtWidgets.QLineEdit()
        self.name.setPlaceholderText(t("project.name"))
        self.lay.addWidget(self.name)
        self.search = QtWidgets.QLineEdit()
        self.search.setPlaceholderText(t("tpl.search"))
        self.search.textChanged.connect(self._fill)
        self.lay.addWidget(self.search)
        self.list = QtWidgets.QListWidget()
        self.list.setMinimumHeight(300)
        self.list.currentItemChanged.connect(self._current)
        self.list.itemDoubleClicked.connect(lambda *_: self.accept())
        self.lay.addWidget(self.list)
        box, _ = _buttons(self, t("create"))
        self.lay.addLayout(box)
        self._fill()

    def name_text(self):
        return self.name.text().strip()

    def _fill(self, *_):
        q = self.search.text().strip().lower()
        self.list.clear()
        last = None
        for tp in self.all:
            label = t(tp["key"])
            if q and q not in label.lower():
                continue
            if tp["group"] != last:
                last = tp["group"]
                h = QtWidgets.QListWidgetItem(t("tpl.group." + last))
                h.setFlags(Qt.NoItemFlags)
                f = h.font()
                f.setBold(True)
                h.setFont(f)
                self.list.addItem(h)
            li = QtWidgets.QListWidgetItem("   " + label)
            li.setData(Qt.UserRole, tp)
            self.list.addItem(li)
        for i in range(self.list.count()):
            if self.list.item(i).data(Qt.UserRole):
                self.list.setCurrentRow(i)
                break

    def _current(self, item, _prev=None):
        if item is not None and item.data(Qt.UserRole):
            self.choice = item.data(Qt.UserRole)


class _ThemeTile(QtWidgets.QPushButton):
    def __init__(self, style_key, pal_key, accent_hex, selected, fa):
        super(_ThemeTile, self).__init__()
        self.pal = th.palette_of(pal_key)
        self.spec = th.STYLE_SPECS[style_key]
        self.style_key = style_key
        self.accent = accent_hex or (th.APP_ACCENT if pal_key.startswith("qp_") else self.pal.accent)
        self.selected = selected
        self.fa = fa
        self.setFixedSize(124, 96)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = self.spec["r"][1]
        pal = self.pal
        p.setBrush(QtGui.QColor(pal.bg))
        p.setPen(QtGui.QPen(QtGui.QColor(self.accent if self.selected else pal.line), 3 if self.selected else 1))
        p.drawRoundedRect(QtCore.QRectF(self.rect()).adjusted(2, 2, -2, -2), r, r)
        p.setBrush(QtGui.QColor(pal.card))
        p.setPen(QtGui.QPen(QtGui.QColor(pal.line)))
        p.drawRoundedRect(QtCore.QRectF(12, 12, self.width() - 24, 44), self.spec["r"][0], self.spec["r"][0])
        p.setPen(Qt.NoPen)
        p.setBrush(QtGui.QColor(self.accent))
        p.drawRoundedRect(22, 22, 52, 6, 3, 3)
        p.setBrush(QtGui.QColor(pal.muted))
        p.setOpacity(0.55)
        p.drawRoundedRect(22, 34, self.width() - 44, 3, 1, 1)
        p.drawRoundedRect(22, 42, 64, 3, 1, 1)
        p.setOpacity(1)
        f = QtGui.QFont(th.family(self.spec["font"]))
        f.setPointSize(10)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QtGui.QColor(pal.text))
        p.drawText(QtCore.QRect(8, 62, self.width() - 16, 26), Qt.AlignCenter, t({"quiet": "quiet", "paper": "paper"}.get(self.style_key, self.style_key)))


class SettingsPage(QtWidgets.QWidget):
    back = Signal()
    changed = Signal()

    def __init__(self, prefs, theme, parent=None):
        super(SettingsPage, self).__init__(parent)
        self.prefs, self.theme = prefs, theme
        self.setObjectName("page")
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        bar = QtWidgets.QFrame()
        bar.setObjectName("bar")
        bl = QtWidgets.QHBoxLayout(bar)
        bl.setContentsMargins(10, 8, 10, 8)
        back = QtWidgets.QToolButton()
        back.setText("←")
        back.setToolTip(t("back"))
        back.clicked.connect(self.back.emit)
        bl.addWidget(back)
        title = QtWidgets.QLabel(t("settings"))
        title.setObjectName("h2")
        bl.addWidget(title)
        bl.addStretch(1)
        outer.addWidget(bar)
        area = QtWidgets.QScrollArea()
        area.setWidgetResizable(True)
        body = QtWidgets.QWidget()
        body.setObjectName("page")
        v = QtWidgets.QVBoxLayout(body)
        v.setContentsMargins(24, 16, 24, 30)
        v.setSpacing(14)
        v.setAlignment(Qt.AlignTop)
        area.setWidget(body)
        outer.addWidget(area, 1)
        pal = th.palette_of(prefs.get("theme"))
        style = th.style_of(pal.key)

        # appearance
        box = self._group(v, t("settings.appearance"))
        row = QtWidgets.QHBoxLayout()
        for text, dark in ((t("light"), False), (t("dark"), True)):
            b = QtWidgets.QPushButton(text)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(pal.dark == dark)
            b.clicked.connect(lambda _=False, d=dark: self._mode(d))
            row.addWidget(b)
        row.addStretch(1)
        box.addWidget(QtWidgets.QLabel(t("mode")))
        box.addLayout(row)
        box.addWidget(QtWidgets.QLabel(t("theme")))
        tiles = QtWidgets.QHBoxLayout()
        tiles.setSpacing(10)
        for key, light, dark in th.STYLES:
            pk = dark if pal.dark else light
            tile = _ThemeTile(key, pk, prefs.get("accent"), key == style, theme.fa)
            tile.clicked.connect(lambda _=False, k=pk: self._theme(k))
            tiles.addWidget(tile)
        tiles.addStretch(1)
        wrap = QtWidgets.QWidget()
        wrap.setLayout(tiles)
        sc = QtWidgets.QScrollArea()
        sc.setWidget(wrap)
        sc.setWidgetResizable(True)
        sc.setFixedHeight(130)
        sc.setFrameShape(QtWidgets.QFrame.NoFrame)
        box.addWidget(sc)
        box.addWidget(QtWidgets.QLabel(t("accent")))
        sw = QtWidgets.QHBoxLayout()
        for hexv in [""] + th.ACCENTS:
            color = hexv or (th.APP_ACCENT if pal.key.startswith("qp_") else pal.accent)
            b = QtWidgets.QPushButton()
            b.setFixedSize(32, 32)
            ring = "3px solid %s" % pal.text if prefs.get("accent") == hexv else "1px solid %s" % pal.line
            b.setStyleSheet("QPushButton { background: %s; border-radius: 16px; border: %s; }" % (color, ring))
            b.clicked.connect(lambda _=False, h=hexv: self._accent(h))
            sw.addWidget(b)
        sw.addStretch(1)
        box.addLayout(sw)

        # editor
        box = self._group(v, t("settings.editor"))
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel(t("font.size")))
        spin = QtWidgets.QSpinBox()
        spin.setRange(8, 28)
        spin.setValue(int(prefs.get("editor_size")))
        spin.valueChanged.connect(lambda x: self._set("editor_size", x))
        row.addWidget(spin)
        row.addStretch(1)
        box.addLayout(row)
        for key, label in (("line_numbers", "line.numbers"), ("wrap", "wrap"), ("auto_pairs", "auto.pairs"), ("symbol_bar", "palette")):
            c = QtWidgets.QCheckBox(t(label))
            c.setChecked(bool(prefs.get(key)))
            c.toggled.connect(lambda on, k=key: self._set(k, on))
            box.addWidget(c)

        # language
        box = self._group(v, t("settings.language"))
        row = QtWidgets.QHBoxLayout()
        for code, label in (("en", "English"), ("fa", "فارسی")):
            b = QtWidgets.QPushButton(label)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(prefs.get("lang") == code)
            b.clicked.connect(lambda _=False, c=code: self._lang(c))
            row.addWidget(b)
        row.addStretch(1)
        box.addLayout(row)

        # about
        box = self._group(v, t("about"))
        n = QtWidgets.QLabel("TeXora")
        n.setObjectName("h2")
        box.addWidget(n)
        tag = QtWidgets.QLabel(t("about.tag.latex"))
        tag.setObjectName("muted")
        tag.setWordWrap(True)
        box.addWidget(tag)
        for label, value in ((t("about.version"), __version__), (t("about.designed"), t("about.author")), (t("about.built"), t("about.claude"))):
            l1 = QtWidgets.QLabel(label)
            l1.setObjectName("muted")
            box.addWidget(l1)
            box.addWidget(QtWidgets.QLabel(value))

    def _group(self, layout, title):
        g = QtWidgets.QGroupBox(title)
        inner = QtWidgets.QVBoxLayout(g)
        inner.setSpacing(10)
        layout.addWidget(g)
        return inner

    def _set(self, k, v):
        self.prefs.set(k, v)
        self.changed.emit()

    def _mode(self, dark):
        pal = th.palette_of(self.prefs.get("theme"))
        style = th.style_of(pal.key)
        for key, l, d in th.STYLES:
            if key == style:
                self.prefs.set("theme", d if dark else l)
        self.changed.emit()

    def _theme(self, key):
        self.prefs.set("theme", key)
        self.changed.emit()

    def _accent(self, hexv):
        self.prefs.set("accent", hexv)
        self.changed.emit()

    def _lang(self, code):
        self.prefs.set("lang", code)
        self.changed.emit()
