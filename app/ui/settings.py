from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class SettingsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('Settings')
        self.setWindowFlags(Qt.Window)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Settings'))
        
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
            }
        """) 