import sys
import subprocess
import pkg_resources
from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt5.QtCore import Qt, QThread, pyqtSignal

REQUIRED_PACKAGES = {
    'pandas': 'pandas',
    'numpy': 'numpy',
    'xlrd': 'xlrd',
    'xlwt': 'xlwt',
    'alembic': 'alembic',
    'passlib': 'passlib',
    'python-jose': 'python-jose[cryptography]',
    'sqlalchemy': 'sqlalchemy',
    'psycopg2-binary': 'psycopg2-binary',
    'python-dotenv': 'python-dotenv',
    'supabase': 'supabase',
    'bcrypt': 'bcrypt',
    'openpyxl': 'openpyxl'
}

class InstallWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, missing_packages):
        super().__init__()
        self.missing_packages = missing_packages

    def run(self):
        try:
            for package in self.missing_packages:
                self.progress.emit(f"Installing {package}...")
                subprocess.check_call([
                    sys.executable, 
                    "-m", 
                    "pip", 
                    "install", 
                    "--user",
                    REQUIRED_PACKAGES[package]
                ])
            self.finished.emit(True, "All packages installed successfully!")
        except Exception as e:
            self.finished.emit(False, f"Error installing packages: {str(e)}")

class DependencyInstaller(QDialog):
    def __init__(self, missing_packages, parent=None):
        super().__init__(parent)
        self.missing_packages = missing_packages
        self.initUI()
        self.start_installation()

    def initUI(self):
        self.setWindowTitle("Installing Dependencies")
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout()
        
        # Status label
        self.status_label = QLabel("Installing required packages...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(self.missing_packages))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Current package label
        self.current_package_label = QLabel("")
        self.current_package_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_package_label)
        
        self.setLayout(layout)
        
        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
                font-size: 12px;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                background-color: #3d3d3d;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
            }
        """)

    def start_installation(self):
        self.worker = InstallWorker(self.missing_packages)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.installation_finished)
        self.worker.start()
        self.progress_count = 0

    def update_progress(self, message):
        self.progress_count += 1
        self.progress_bar.setValue(self.progress_count)
        self.current_package_label.setText(message)

    def installation_finished(self, success, message):
        if success:
            QMessageBox.information(self, "Success", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Error", message)
            self.reject()

def check_dependencies():
    """Check if all required packages are installed and install missing ones."""
    missing_packages = []
    
    # Check installed packages
    installed_packages = {pkg.key for pkg in pkg_resources.working_set}
    
    for package in REQUIRED_PACKAGES:
        if package not in installed_packages:
            missing_packages.append(package)
    
    if missing_packages:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Missing Dependencies")
        msg.setText("Some required packages are missing.")
        msg.setInformativeText(
            f"The following packages need to be installed:\n\n"
            f"{', '.join(missing_packages)}\n\n"
            "Would you like to install them now?"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        
        if msg.exec_() == QMessageBox.Yes:
            installer = DependencyInstaller(missing_packages)
            result = installer.exec_()
            
            if result == QDialog.Accepted:
                # Refresh the working set to include newly installed packages
                pkg_resources.working_set = pkg_resources.WorkingSet()
                return True
            return False
            
        return False
    
    return True 