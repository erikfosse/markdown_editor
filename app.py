import html
import subprocess
from pathlib import Path
import sys

from PyQt5.QtCore import QPoint, Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QColor, QPainter, QTextFormat, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QMainWindow,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QMessageBox,
    QToolBar,
    QWidget,
    QAction,
    QVBoxLayout,
)

try:
    import markdown as md
except ImportError:
    md = None


DEFAULT_TEXT = """# Markdown Editor

Type markdown on the left and see the rendered output on the right.

## Examples

- **Bold text**
- *Italic text*
- [A link](https://example.com)

```python
print("Hello, markdown!")
```
"""

BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "documents"
STYLESHEET_FILE = BASE_DIR / "styles.css"


def render_markdown(text: str) -> str:
    if md is not None:
        return md.markdown(
            text,
            extensions=["fenced_code", "tables", "nl2br", "codehilite"],
        )

    escaped = html.escape(text).replace("\n", "<br>")
    return f"<pre>{escaped}</pre>"


def preview_html(body: str) -> str:
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
html {{
    background: #111827;
}}
body {{
    background: #111827;
    color: #e5e7eb;
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.6;
    padding: 28px 32px;
    margin: 0;
}}
a {{ color: #60a5fa; }}
code {{
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
}}
pre {{
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 14px;
    overflow-x: auto;
    line-height: 1.5;
}}
pre code {{
    background: transparent;
    border: none;
    padding: 0;
    border-radius: 0;
}}
blockquote {{
    border-left: 4px solid #334155;
    margin: 0;
    padding-left: 12px;
    color: #cbd5e1;
}}
h1, h2, h3, h4, h5, h6 {{
    color: #f8fafc;
}}
.codehilite {{
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
}}
.codehilite pre {{
    background: transparent;
    border: 0;
    margin: 0;
}}
.codehilite .hll {{ background-color: #1e293b; }}
.codehilite .c {{ color: #64748b; font-style: italic; }}
.codehilite .k {{ color: #c084fc; }}
.codehilite .o {{ color: #f97316; }}
.codehilite .ch, .codehilite .cm, .codehilite .cp, .codehilite .cpf, .codehilite .c1, .codehilite .cs {{ color: #64748b; }}
.codehilite .gd {{ color: #fca5a5; }}
.codehilite .gi {{ color: #86efac; }}
.codehilite .gh {{ color: #e5e7eb; font-weight: bold; }}
.codehilite .gp {{ color: #94a3b8; }}
.codehilite .gr {{ color: #f87171; }}
.codehilite .gt {{ color: #f87171; }}
.codehilite .kc, .codehilite .kd, .codehilite .kn, .codehilite .kp, .codehilite .kr {{ color: #c084fc; }}
.codehilite .kt {{ color: #38bdf8; }}
.codehilite .m, .codehilite .mf, .codehilite .mh, .codehilite .mi, .codehilite .mo, .codehilite .il {{ color: #f59e0b; }}
.codehilite .s, .codehilite .sa, .codehilite .sb, .codehilite .sc, .codehilite .dl, .codehilite .sd, .codehilite .s2, .codehilite .sh, .codehilite .si, .codehilite .sx, .codehilite .sr, .codehilite .s1, .codehilite .ss {{ color: #34d399; }}
.codehilite .na {{ color: #60a5fa; }}
.codehilite .nb {{ color: #e5e7eb; }}
.codehilite .nc {{ color: #22d3ee; }}
.codehilite .no {{ color: #f472b6; }}
.codehilite .nd {{ color: #c084fc; }}
.codehilite .ni {{ color: #f8fafc; }}
.codehilite .ne {{ color: #fb7185; }}
.codehilite .nf {{ color: #38bdf8; }}
.codehilite .nl {{ color: #e5e7eb; }}
.codehilite .nn {{ color: #cbd5e1; }}
.codehilite .nx {{ color: #e5e7eb; }}
.codehilite .py {{ color: #e5e7eb; }}
.codehilite .nt {{ color: #60a5fa; }}
.codehilite .nv {{ color: #f9a8d4; }}
.codehilite .w {{ color: #94a3b8; }}
</style>
</head>
<body>{body}</body>
</html>"""


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return self.code_editor.line_number_area_size()

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def line_number_area_size(self):
        return self.line_number_area.width()

    def line_number_area_width(self):
        digits = len(str(max(1, self.blockCount())))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(
                0, rect.y(), self.line_number_area.width(), rect.height()
            )

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            cr.left(),
            cr.top(),
            self.line_number_area_width(),
            cr.height(),
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#111827"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(
            self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        )
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#7c8aa5"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    number,
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self):
        selection = QTextEdit.ExtraSelection()
        line_color = QColor("#13213a")
        selection.format.setBackground(line_color)
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


class TitleBar(QFrame):
    def __init__(self, window: QMainWindow):
        super().__init__(window)
        self.window = window
        self._drag_position: QPoint | None = None
        self.setObjectName("TitleBar")
        self.setFixedHeight(42)

        self.title_label = QLabel(window.windowTitle())
        self.title_label.setObjectName("TitleBarTitle")

        self.min_button = QPushButton("–")
        self.max_button = QPushButton("□")
        self.close_button = QPushButton("×")

        for button in (self.min_button, self.max_button, self.close_button):
            button.setFixedSize(38, 28)

        self.min_button.clicked.connect(self.minimize_window)
        self.max_button.clicked.connect(self.toggle_maximize)
        self.close_button.clicked.connect(window.close)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.min_button)
        layout.addWidget(self.max_button)
        layout.addWidget(self.close_button)

    def set_title(self, title: str):
        self.title_label.setText(title)

    def minimize_window(self):
        self.window.setWindowState(self.window.windowState() | Qt.WindowMinimized)
        self.window.showMinimized()

    def toggle_maximize(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPos() - self.window.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None and event.buttons() & Qt.LeftButton and not self.window.isMaximized():
            self.window.move(event.globalPos() - self._drag_position)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_maximize()
            event.accept()
        super().mouseDoubleClickEvent(event)


class MarkdownEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("Markdown Editor")
        self.resize(1100, 700)
        DOCUMENTS_DIR.mkdir(exist_ok=True)
        self.current_file: Path | None = None

        self.title_bar = TitleBar(self)
        self.editor = CodeEditor()
        self.editor.setPlainText(DEFAULT_TEXT)
        self.editor.setPlaceholderText("Write markdown here...")

        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        self.preview.setOpenLinks(False)
        self.preview.anchorClicked.connect(self.open_link)
        self.preview.setStyleSheet("""
                                   background: #111827; 
                                   border: none; 
                                   padding: 20px 30px 10px 30px;
                                   """)

        toolbar = QToolBar("File")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)

        save_as_action = QAction("Save As", self)
        save_as_action.triggered.connect(self.save_file_as)
        toolbar.addAction(save_as_action)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        splitter.setSizes([550, 550])
        splitter.setHandleWidth(12)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        layout.addWidget(toolbar)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

        self.editor.textChanged.connect(self.update_preview)
        self.update_preview()

    def update_preview(self):
        self.preview.setHtml(preview_html(render_markdown(self.editor.toPlainText())))

    def open_link(self, url: QUrl):
        if not url.isValid():
            return

        if QDesktopServices.openUrl(url):
            return

        if (
            sys.platform.startswith("linux")
            and Path("/mnt/c/Windows/explorer.exe").exists()
        ):
            subprocess.Popen(["/mnt/c/Windows/explorer.exe", url.toString()])
            return

        if (
            sys.platform.startswith("linux")
            and Path("/mnt/c/Windows/system32/cmd.exe").exists()
        ):
            subprocess.Popen(
                ["/mnt/c/Windows/system32/cmd.exe", "/c", "start", "", url.toString()]
            )

    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Markdown File",
            str(DOCUMENTS_DIR),
            "Markdown Files (*.md *.markdown);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Open Failed", f"Could not open file:\n{exc}")
            return

        self.current_file = path
        self.editor.setPlainText(text)
        self.update_window_title()

    def save_file(self):
        if self.current_file is None:
            self.save_file_as()
            return

        self.write_file(self.current_file)

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Markdown File",
            str(DOCUMENTS_DIR / "untitled.md"),
            "Markdown Files (*.md);;All Files (*)",
        )
        if not file_path:
            return

        path = Path(file_path)
        if path.suffix.lower() not in {".md", ".markdown"}:
            path = path.with_suffix(".md")

        self.write_file(path)

    def write_file(self, path: Path):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.critical(self, "Save Failed", f"Could not save file:\n{exc}")
            return

        self.current_file = path
        self.update_window_title()

    def update_window_title(self):
        name = self.current_file.name if self.current_file else "Untitled"
        title = f"Markdown Editor - {name}"
        self.setWindowTitle(title)
        self.title_bar.set_title(title)


def main():
    app = QApplication(sys.argv)
    stylesheet_path = STYLESHEET_FILE
    if stylesheet_path.exists():
        app.setStyleSheet(stylesheet_path.read_text(encoding="utf-8"))
    window = MarkdownEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
