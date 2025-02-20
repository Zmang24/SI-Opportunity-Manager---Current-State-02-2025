from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit,
                           QPushButton, QMessageBox, QCheckBox, QHBoxLayout,
                           QDialog, QFormLayout)
from PyQt5.QtCore import pyqtSignal, QSettings
from app.auth.auth_handler import hash_pin, create_access_token
from app.database.connection import get_db_with_retry
from app.models.models import User
from sqlalchemy import func
from datetime import datetime

class PinResetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Reset PIN")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Form layout
        form = QFormLayout()
        form.setSpacing(10)
        
        # Username field
        self.username = QLineEdit()
        self.username.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #3d3d3d;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
        """)
        form.addRow("Username:", self.username)
        
        # Email field
        self.email = QLineEdit()
        self.email.setStyleSheet(self.username.styleSheet())
        form.addRow("Email:", self.email)
        
        # New PIN field
        self.new_pin = QLineEdit()
        self.new_pin.setEchoMode(QLineEdit.Password)
        self.new_pin.setStyleSheet(self.username.styleSheet())
        form.addRow("New PIN:", self.new_pin)
        
        # Confirm PIN field
        self.confirm_pin = QLineEdit()
        self.confirm_pin.setEchoMode(QLineEdit.Password)
        self.confirm_pin.setStyleSheet(self.username.styleSheet())
        form.addRow("Confirm PIN:", self.confirm_pin)
        
        layout.addLayout(form)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset PIN")
        reset_btn.clicked.connect(self.reset_pin)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #d83b01;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #ea4a1f;
            }
            QPushButton:pressed {
                background-color: #b83301;
            }
        """)
        
        button_layout.addWidget(reset_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Set window properties
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: white;
            }
        """)
        self.setWindowTitle("Reset PIN")
        self.setFixedSize(400, 300)
        
    def reset_pin(self):
        username = self.username.text().strip()
        email = self.email.text().strip()
        new_pin = self.new_pin.text()
        confirm_pin = self.confirm_pin.text()
        
        if not all([username, email, new_pin, confirm_pin]):
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return
            
        if new_pin != confirm_pin:
            QMessageBox.warning(self, "Error", "PINs do not match")
            return
            
        try:
            db = get_db_with_retry()
            try:
                user = db.query(User).filter(
                    User.username == username,
                    User.email == email,
                    User.is_active == True
                ).first()
                
                if user:
                    # Update PIN
                    user.pin = hash_pin(new_pin)
                    user.updated_at = datetime.utcnow()
                    db.commit()
                    
                    QMessageBox.information(self, "Success", "PIN has been reset successfully!")
                    self.accept()
                else:
                    QMessageBox.warning(self, "Error", "Invalid username or email")
            finally:
                db.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset PIN: {str(e)}")

class AuthWidget(QWidget):
    authenticated = pyqtSignal(User)
    create_account_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.settings = QSettings('SI Opportunity Manager', 'Auth')
        self.initUI()
        self.load_remembered_username()
        
    def closeEvent(self, event):
        # Hide the window instead of closing it
        event.ignore()
        self.hide()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Welcome message
        welcome_label = QLabel("Welcome to SI Opportunity Manager")
        welcome_label.setStyleSheet("""
            font-size: 24px;
            margin-bottom: 20px;
            color: white;
            font-weight: bold;
            padding: 10px 0;
        """)
        welcome_label.setWordWrap(True)  # Enable word wrap
        layout.addWidget(welcome_label)
        
        # Username input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #555555;
                border-radius: 4px;
                margin-bottom: 10px;
                background-color: #3d3d3d;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
            QLineEdit::placeholder {
                color: #999999;
            }
        """)
        layout.addWidget(self.username_input)
        
        # PIN input
        self.pin_input = QLineEdit()
        self.pin_input.setPlaceholderText("Enter your PIN")
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setStyleSheet(self.username_input.styleSheet())
        layout.addWidget(self.pin_input)
        
        # Remember me checkbox
        self.remember_me = QCheckBox("Remember me")
        self.remember_me.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 13px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555555;
                border-radius: 3px;
                background-color: #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QCheckBox::indicator:hover {
                border-color: #0078d4;
            }
        """)
        layout.addWidget(self.remember_me)
        
        # Login button
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self.authenticate)
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 10px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        layout.addWidget(login_btn)
        
        # Links layout
        links_layout = QHBoxLayout()
        links_layout.setSpacing(20)
        
        # Create account link
        create_account_btn = QPushButton("Create New Account")
        create_account_btn.clicked.connect(self.create_account_requested.emit)
        create_account_btn.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #0078d4;
                text-decoration: underline;
                padding: 5px;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #2196F3;
            }
        """)
        links_layout.addWidget(create_account_btn)
        
        # Reset PIN link
        reset_pin_btn = QPushButton("Reset PIN")
        reset_pin_btn.clicked.connect(self.reset_pin)
        reset_pin_btn.setStyleSheet(create_account_btn.styleSheet())
        links_layout.addWidget(reset_pin_btn)
        
        layout.addLayout(links_layout)
        
        # Add some spacing
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Set window properties
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QMessageBox {
                background-color: #2b2b2b;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
            }
            QMessageBox QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.setFixedSize(400, 500)
        
    def authenticate(self):
        username = self.username_input.text()
        pin = self.pin_input.text()
        
        if not username or not pin:
            QMessageBox.warning(self, "Error", "Please enter both username and PIN")
            return
            
        pin_hash = hash_pin(pin)
        
        try:
            db = get_db_with_retry()  # Use the retry logic
            try:
                user = db.query(User).filter(
                    User.username == username,
                    User.pin == pin_hash,
                    User.is_active == True
                ).first()
                
                if user:
                    now = datetime.utcnow()
                    # Update last login and last active
                    user.last_login = now
                    user.last_active = now
                    db.commit()
                    
                    # Handle remember me
                    if self.remember_me.isChecked():
                        self.settings.setValue('remembered_username', username)
                    else:
                        self.settings.remove('remembered_username')
                    
                    # Create JWT token
                    token = create_access_token(str(user.id))
                    # Store token (you might want to store this in the main application)
                    user.token = token
                    self.authenticated.emit(user)
                    self.clear_fields()
                else:
                    QMessageBox.warning(self, "Error", "Invalid username or PIN")
            except Exception as e:
                db.rollback()
                QMessageBox.critical(self, "Database Error", f"An error occurred: {str(e)}")
            finally:
                db.close()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Could not connect to the database: {str(e)}")
            
    def clear_fields(self):
        """Clear input fields"""
        if not self.remember_me.isChecked():
            self.username_input.clear()
        self.pin_input.clear()
        
    def load_remembered_username(self):
        """Load remembered username if exists"""
        remembered_username = self.settings.value('remembered_username')
        if remembered_username:
            self.username_input.setText(remembered_username)
            self.remember_me.setChecked(True)
            
    def reset_pin(self):
        """Handle PIN reset request"""
        dialog = PinResetDialog(self)
        if self.username_input.text():
            dialog.username.setText(self.username_input.text())
        dialog.exec_() 