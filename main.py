# 原来的代码保留
from ui.main_win import MainWindow
import sys
from PyQt6.QtWidgets import QApplication

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("QWidget { font-family: Microsoft YaHei; }")
    win = MainWindow()
    win.show()
    qr = win.frameGeometry()
    cp = app.primaryScreen().availableGeometry().center()
    qr.moveCenter(cp)
    win.move(qr.topLeft())
    sys.exit(app.exec())