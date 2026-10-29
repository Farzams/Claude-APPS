"""One place that knows which Qt binding is in use.  The Windows 7 build uses PySide2 (Qt 5.15, the last Qt that runs on
Windows 7); PySide6 is accepted too so that the app can be developed and tested on current systems."""
try:
    from PySide2 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets, QtWebChannel  # noqa: F401
    from PySide2.QtCore import Qt, Signal, Slot, QObject, QTimer, QUrl, QSize, QPoint, QRect, QEvent, QThread  # noqa: F401
    QT_MAJOR = 5
    QAction = QtWidgets.QAction
    QShortcut = QtWidgets.QShortcut
    QWebEnginePage = QtWebEngineWidgets.QWebEnginePage
    QWebEngineView = QtWebEngineWidgets.QWebEngineView
    QWebEngineScript = QtWebEngineWidgets.QWebEngineScript
except ImportError:  # pragma: no cover - development machines
    from PySide6 import QtCore, QtGui, QtWidgets, QtWebEngineWidgets, QtWebChannel, QtWebEngineCore  # noqa: F401
    from PySide6.QtCore import Qt, Signal, Slot, QObject, QTimer, QUrl, QSize, QPoint, QRect, QEvent, QThread  # noqa: F401
    QT_MAJOR = 6
    QAction = QtGui.QAction
    QShortcut = QtGui.QShortcut
    QWebEnginePage = QtWebEngineCore.QWebEnginePage
    QWebEngineView = QtWebEngineWidgets.QWebEngineView
    QWebEngineScript = QtWebEngineCore.QWebEngineScript


def run_dialog(dlg):
    return dlg.exec() if hasattr(dlg, "exec") else dlg.exec_()


def run_app(app):
    return app.exec() if hasattr(app, "exec") else app.exec_()
