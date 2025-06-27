from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QMessageBox, QComboBox, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from app.database.connection import SessionLocal
from app.models.models import User
from app.auth.auth_handler import hash_pin
from datetime import datetime

class AccountCreationWidget(QWidget):
    account_created = pyqtSignal(User)
    
    # Define constants
    DEPARTMENT = "Information Solutions"
    TEAMS = ["ID3", "SI", "Email", "Advanced Projects"]
    ROLE_KEYS = {
        "MGRPROTECH9716": "manager",
        "ADMPROTECH2025": "admin"
    }
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def closeEvent(self, event):
        # Hide the window instead of closing it
        event.ignore()
        self.hide()
        
    def initUI(self):
        # Main layout with margins for better spacing
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Create a container frame for the form
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(16)
        
        # Title
        title = QLabel("Create Account")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        """)
        form_layout.addWidget(title)
        
        # Form fields
        self.fields = {}
        
        # Required fields with labels
        field_configs = [
            ("username", "Username:", "text"),
            ("email", "Email:", "text"),
            ("pin", "PIN:", "password"),
            ("pin_confirm", "Confirm PIN:", "password"),
            ("first_name", "First Name:", "text"),
            ("last_name", "Last Name:", "text"),
            ("team", "Team:", "combo", self.TEAMS),
            ("department", "Department:", "readonly", self.DEPARTMENT),
            ("role_key", "Role Access Key:", "password")
        ]
        
        # Common styles
        input_style = """
            QLineEdit {
                background-color: #3d3d3d;
                color: white;
                padding: 8px;
                border: 1px solid #555555;
                border-radius: 4px;
                min-width: 300px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
            QLineEdit:disabled {
                background-color: #2b2b2b;
                color: #888888;
            }
        """
        
        combo_style = """
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                padding: 8px;
                border: 1px solid #555555;
                border-radius: 4px;
                min-width: 300px;
            }
            QComboBox:hover {
                border: 1px solid #666666;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid white;
            }
            QComboBox QAbstractItemView {
                background-color: #3d3d3d;
                color: white;
                selection-background-color: #0078d4;
                border: 1px solid #555555;
            }
        """
        
        label_style = """
            QLabel {
                color: white;
                font-size: 14px;
            }
        """
        
        for config in field_configs:
            field_id, label_text, field_type, *extra = config
            field_layout = QHBoxLayout()
            
            # Create label container for fields that need help icons
            label_container = QHBoxLayout()
            label_container.setSpacing(5)
            
            # Create and add label
            label = QLabel(label_text)
            label.setMinimumWidth(120)
            label.setStyleSheet(label_style)
            label_container.addWidget(label)
            
            # Add help icon for role key field
            if field_id == "role_key":
                help_label = QLabel("(?)")
                help_label.setStyleSheet("""
                    QLabel {
                        color: #0078d4;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 2px 4px;
                        border-radius: 8px;
                    }
                    QLabel:hover {
                        background-color: #3d3d3d;
                    }
                """)
                help_label.setMouseTracking(True)
                help_label.setCursor(Qt.WhatsThisCursor)
                help_label.setToolTipDuration(10000)
                help_label.setToolTip(
                    "The Role Access Key is optional and is used to grant elevated privileges.\n\n"
                    "• Leave empty for a standard user account\n"
                    "• Enter the provided key if you've been assigned manager or admin privileges\n\n"
                    "Contact your system administrator if you need elevated access."
                )
                label_container.addWidget(help_label)
            
            label_container.addStretch()
            field_layout.addLayout(label_container)
            
            # Create and configure field based on type
            if field_type == "password":
                field = QLineEdit()
                field.setEchoMode(QLineEdit.Password)
                field.setStyleSheet(input_style)
            elif field_type == "text":
                field = QLineEdit()
                field.setStyleSheet(input_style)
            elif field_type == "combo":
                field = QComboBox()
                field.addItems(extra[0])
                field.setStyleSheet(combo_style)
            elif field_type == "readonly":
                field = QLineEdit(extra[0])
                field.setReadOnly(True)
                field.setStyleSheet(input_style + """
                    QLineEdit:disabled {
                        background-color: #2b2b2b;
                        color: #888888;
                    }
                """)
            
            # Add placeholder for role key
            if field_id == "role_key":
                field.setPlaceholderText("Enter access key if provided")
            
            field_layout.addWidget(field)
            self.fields[field_id] = field
            form_layout.addLayout(field_layout)
        
        # Create account button
        create_btn = QPushButton("Create Account")
        create_btn.clicked.connect(self.create_account)
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 150px;
                margin-top: 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        form_layout.addWidget(create_btn, alignment=Qt.AlignCenter)
        
        # Add container to main layout
        layout.addWidget(form_frame)
        
        # Set window properties
        self.setLayout(layout)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
            QMessageBox {
                background-color: #2b2b2b;
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
                min-width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        self.setWindowTitle("Create Account")
        self.resize(650, 720)
        
    def create_account(self):
        # Validate fields
        for field_id, field in self.fields.items():
            if field_id not in ['role_key', 'department'] and not (isinstance(field, QLineEdit) and field.text().strip() or isinstance(field, QComboBox) and field.currentText()):
                QMessageBox.warning(self, "Error", f"Please fill in the {field_id.replace('_', ' ').title()}")
                return
        
        # Validate PIN match
        if self.fields["pin"].text() != self.fields["pin_confirm"].text():
            QMessageBox.warning(self, "Error", "PINs do not match")
            return
        
        # Validate email format (improved check)
        email = self.fields["email"].text().strip()
        if not self.is_valid_email(email):
            QMessageBox.warning(self, "Error", "Please enter a valid email address (e.g., user@example.com)")
            return
        
        # Validate PIN complexity
        pin = self.fields["pin"].text()
        if not self.is_valid_pin(pin):
            QMessageBox.warning(self, "Error", "PIN must be at least 4 characters long")
            return
        
        # Validate role key and determine role
        role_key = self.fields["role_key"].text()
        role = self.ROLE_KEYS.get(role_key, "user")
        
        # Create user
        db = SessionLocal()
        try:
            # Check if username exists
            existing_user = db.query(User).filter(User.username == self.fields["username"].text()).first()
            if existing_user:
                QMessageBox.warning(self, "Error", "Username already exists")
                return
            
            # Check if email exists
            existing_email = db.query(User).filter(User.email == email).first()
            if existing_email:
                QMessageBox.warning(self, "Error", "Email address already exists")
                return
            
            # Create new user
            new_user = User(
                username=self.fields["username"].text(),
                email=self.fields["email"].text(),
                pin=hash_pin(self.fields["pin"].text()),
                first_name=self.fields["first_name"].text(),
                last_name=self.fields["last_name"].text(),
                team=self.fields["team"].currentText(),
                department=self.DEPARTMENT,
                role=role,
                is_active=True,
                notifications_enabled=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(new_user)
            db.commit()
            
            role_msg = f" with {role} privileges" if role in ["manager", "admin"] else ""
            QMessageBox.information(self, "Success", f"Account created successfully{role_msg}!")
            self.account_created.emit(new_user)
            self.clear_fields()
            
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Failed to create account: {str(e)}")
        finally:
            db.close()
    
    def clear_fields(self):
        """Clear all input fields"""
        for field_id, field in self.fields.items():
            if isinstance(field, QLineEdit) and field_id != 'department':
                field.clear()
            elif isinstance(field, QComboBox):
                field.setCurrentIndex(0)
    
    def is_valid_email(self, email):
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def is_valid_pin(self, pin):
        """Validate PIN complexity"""
        return len(pin) >= 4 