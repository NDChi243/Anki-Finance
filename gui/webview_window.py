# -*- coding: utf-8 -*-

import os
from aqt.qt import (
    QDialog, QVBoxLayout, QWebEngineView,
    QWebChannel, Qt, QSize, QUrl,
)
from .web_bridge import TycoonBridge


class TycoonWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anki Finance")
        self.setMinimumSize(920, 650)
        self.resize(1020, 720)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web = QWebEngineView(self)
        layout.addWidget(self.web)

        self.channel = QWebChannel(self.web.page())
        self.bridge = TycoonBridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self.web.page().setWebChannel(self.channel)

        html_path = os.path.join(os.path.dirname(__file__), "tycoon_ui.html")
        self.web.load(QUrl.fromLocalFile(html_path))

    def sizeHint(self):
        return QSize(1020, 720)
