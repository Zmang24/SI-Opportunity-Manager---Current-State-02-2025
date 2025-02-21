from typing import Dict, Optional, Union, List, cast
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QFormLayout, QFrame,
                           QMessageBox, QScrollArea, QComboBox)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QShowEvent, QCloseEvent
from app.database.connection import SessionLocal
from app.models.models import User, Opportunity
from app.auth.auth_handler import hash_pin
from sqlalchemy import update
import traceback

class ProfileWidget(QWidget):
    profile_updated = pyqtSignal()
    
    def __init__(self, current_user: User):
        super().__init__()
        self.current_user = current_user
        self.fields: Dict[str, Union[QLineEdit, QComboBox]] = {}
        self.stats_labels: Dict[str, QLabel] = {}
        self.initUI()
        
    def showEvent(self, a0: QShowEvent) -> None:
        """Update statistics when the profile is shown"""
        super().showEvent(a0)
        self.load_statistics()
        
        # Set echo mode for password fields
        for field_name in ['pin', 'new_pin', 'confirm_pin']:
            field = self.fields.get(field_name)
            if isinstance(field, QLineEdit):
                field.setEchoMode(QLineEdit.EchoMode.Password)  # type: ignore
        
    def closeEvent(self, a0: QCloseEvent) -> None:
        """Handle close event"""
        super().closeEvent(a0)
        a0.ignore()
        self.hide()
        
    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #2b2b2b;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d2d2d;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #4d4d4d;
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        # Container widget for scroll area
        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setSpacing(20)
        
        # Header section
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #3d3d3d;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        header_layout = QVBoxLayout()
        
        # Profile title
        title = QLabel("User Profile")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(title)
        
        # User role badge
        role_badge = QLabel(self.current_user.role.upper())
        role_badge.setStyleSheet(f"""
            background-color: {'#0078d4' if self.current_user.role == 'admin' 
                             else '#107c10' if self.current_user.role == 'manager' 
                             else '#5c2d91'};
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 12px;
        """)
        role_badge.setFixedWidth(role_badge.sizeHint().width() + 24)
        header_layout.addWidget(role_badge)
        
        header.setLayout(header_layout)
        container_layout.addWidget(header)
        
        # User info section
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #3d3d3d;
                border-radius: 10px;
                padding: 20px;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:disabled {
                background-color: #404040;
                color: #888888;
            }
            QComboBox {
                background-color: #2b2b2b;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px;
                color: white;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid white;
                margin-right: 8px;
            }
        """)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Create fields
        field_configs = [
            ("username", "Username:", True),
            ("email", "Email:", False),
            ("first_name", "First Name:", False),
            ("last_name", "Last Name:", False),
            ("team", "Team:", False, ["ID3", "SI", "Email", "Advanced Projects"]),
            ("department", "Department:", True),
            ("role", "Role:", True),
        ]
        
        for config in field_configs:
            field_id, label, readonly, *extra = config
            label_widget = QLabel(label)
            self.create_field(field_id, label, not readonly, extra if extra else None)
            form_layout.addRow(label_widget, self.fields[field_id])
            
        # Add PIN change section
        pin_section = QFrame()
        pin_section.setStyleSheet(info_frame.styleSheet())
        pin_layout = QVBoxLayout()
        
        pin_title = QLabel("Change PIN")
        pin_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        pin_layout.addWidget(pin_title)
        
        pin_form = QFormLayout()
        self.current_pin = QLineEdit()
        self.current_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pin = QLineEdit()
        self.new_pin.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pin = QLineEdit()
        self.confirm_pin.setEchoMode(QLineEdit.EchoMode.Password)
        
        pin_form.addRow("Current PIN:", self.current_pin)
        pin_form.addRow("New PIN:", self.new_pin)
        pin_form.addRow("Confirm PIN:", self.confirm_pin)
        pin_layout.addLayout(pin_form)
        
        pin_section.setLayout(pin_layout)
        
        # Add appearance section
        appearance_section = QFrame()
        appearance_section.setStyleSheet(info_frame.styleSheet())
        appearance_layout = QVBoxLayout()
        
        appearance_title = QLabel("Appearance Settings")
        appearance_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        appearance_layout.addWidget(appearance_title)
        
        # Icon color theme selector
        theme_form = QFormLayout()
        self.color_theme = QComboBox()
        self.color_theme.addItems([
            "Rainbow Animation",
            "White Icons",
            "Blue Theme",
            "Green Theme",
            "Purple Theme"
        ])
        
        # Set current theme based on user preference
        current_theme = getattr(self.current_user, 'icon_theme', 'Rainbow Animation')
        print(f"Current user theme: {current_theme}")  # Debug print
        self.color_theme.setCurrentText(current_theme)
        
        theme_form.addRow("Icon Color Theme:", self.color_theme)
        appearance_layout.addLayout(theme_form)
        
        # Add preview text
        preview_label = QLabel("Changes will take effect after saving and reopening windows.")
        preview_label.setStyleSheet("color: #888888; font-style: italic; font-size: 12px;")
        appearance_layout.addWidget(preview_label)
        
        appearance_section.setLayout(appearance_layout)
        
        # Statistics section
        stats_frame = QFrame()
        stats_frame.setStyleSheet(info_frame.styleSheet())
        stats_layout = QVBoxLayout()
        
        stats_title = QLabel("Activity Statistics")
        stats_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        stats_layout.addWidget(stats_title)
        
        # Add statistics
        stats_configs = [
            ("total_opportunities", "Total Opportunities Created:"),
            ("accepted_opportunities", "Total Opportunities Accepted:"),
            ("active_opportunities", "Active Opportunities:"),
            ("completed_opportunities", "Completed Opportunities:"),
            ("avg_response_time", "Average Response Time:"),
            ("last_login", "Last Login:"),
            ("account_created", "Account Created:")
        ]
        
        for stat_id, label in stats_configs:
            stat_label = QLabel()
            self.stats_labels[stat_id] = stat_label
            stats_layout.addWidget(QLabel(label))
            stats_layout.addWidget(stat_label)
            
        stats_frame.setLayout(stats_layout)
        
        # Add all sections to form
        info_frame.setLayout(form_layout)
        container_layout.addWidget(info_frame)
        container_layout.addWidget(pin_section)
        container_layout.addWidget(appearance_section)
        container_layout.addWidget(stats_frame)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self.save_changes)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.hide)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #d83b01;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ea4a1f;
            }
            QPushButton:pressed {
                background-color: #b83301;
            }
        """)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        container_layout.addLayout(button_layout)
        container_layout.addStretch()
        
        # Set container layout
        container.setLayout(container_layout)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        self.load_statistics()
        
        # Set window properties
        self.setWindowTitle("User Profile")
        self.resize(600, 800)
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
        
    def create_field(self, name: str, label: str, is_editable: bool, extra: Optional[List[List[str]]] = None) -> None:
        """Create a form field"""
        if extra and extra[0]:  # Combo box
            field = QComboBox()
            field.addItems(extra[0])
            field.setCurrentText(str(getattr(self.current_user, name, '')))
        else:
            field = QLineEdit()
            field.setText(str(getattr(self.current_user, name, '')))
            field.setReadOnly(not is_editable)
            
            if name in ['pin', 'new_pin', 'confirm_pin']:
                field.setEchoMode(QLineEdit.EchoMode.Password)
            
        self.fields[name] = field
            
    def load_statistics(self) -> None:
        """Load and display user statistics"""
        with SessionLocal() as db:
            try:
                # Get opportunities created by the user
                created_opps = db.query(Opportunity).filter(
                    Opportunity.creator_id == self.current_user.id
                ).all()
                print(f"Created opportunities: {len(created_opps)}")
                
                # Get opportunities accepted by the user
                accepted_opps = db.query(Opportunity).filter(
                    Opportunity.acceptor_id == self.current_user.id
                ).all()
                print(f"Accepted opportunities: {len(accepted_opps)}")
                
                # Get active opportunities (both created and accepted)
                active_opps = db.query(Opportunity).filter(
                    (Opportunity.creator_id == self.current_user.id) | 
                    (Opportunity.acceptor_id == self.current_user.id),
                    Opportunity.status.ilike("new") |
                    Opportunity.status.ilike("in progress") |
                    Opportunity.status.ilike("needs info")
                ).all()
                print(f"Active opportunities: {len(active_opps)}")
                
                # Get completed opportunities with case-insensitive comparison
                completed_opps = db.query(Opportunity).filter(
                    (Opportunity.creator_id == self.current_user.id) | 
                    (Opportunity.acceptor_id == self.current_user.id),
                    Opportunity.status.ilike("completed")
                ).all()
                
                # Debug logging for completed opportunities
                print(f"Completed opportunities found: {len(completed_opps)}")
                for opp in completed_opps:
                    print(f"Completed opp - ID: {opp.id}, Status: {opp.status}, Creator: {opp.creator_id}, Acceptor: {opp.acceptor_id}")
                
                # Calculate statistics
                total_created = len(created_opps)
                total_accepted = len(accepted_opps)
                total_active = len(active_opps)
                total_completed = len(completed_opps)
                
                # Calculate average response time for opportunities
                response_times = []
                
                # Include both accepted and completed opportunities for response time calculation
                all_handled_opps = []
                seen_ids = set()  # To avoid counting the same opportunity twice
                
                for opp in accepted_opps + completed_opps:
                    if opp.id not in seen_ids:
                        all_handled_opps.append(opp)
                        seen_ids.add(opp.id)
                
                print(f"Total handled opportunities for response time: {len(all_handled_opps)}")
                
                for opp in all_handled_opps:
                    # Skip if user is the creator (we want response time for tickets they handle)
                    if opp.creator_id == self.current_user.id:
                        continue
                        
                    # Calculate response time based on available timestamps
                    created_time = opp.created_at
                    response_time = None
                    
                    # Try different timestamps in order of preference
                    if opp.started_at and created_time:
                        response_time = opp.started_at - created_time
                        print(f"Using started_at for ticket {opp.id}")
                    elif opp.accepted_at and created_time:
                        response_time = opp.accepted_at - created_time
                        print(f"Using accepted_at for ticket {opp.id}")
                    elif opp.status.lower() == "completed" and opp.completed_at and created_time:
                        response_time = opp.completed_at - created_time
                        print(f"Using completed_at for ticket {opp.id}")
                    
                    if response_time:
                        hours = response_time.total_seconds() / 3600
                        print(f"Response time for ticket {opp.id}: {hours:.1f} hours")
                        response_times.append(hours)
                
                # Calculate average response time
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    print(f"Average response time: {avg_response_time:.1f} hours")
                else:
                    avg_response_time = 0
                    print("No response times available")
                
                # Update statistics labels with better formatting
                self.stats_labels['total_opportunities'].setText(f"{total_created:,}")
                self.stats_labels['accepted_opportunities'].setText(f"{total_accepted:,}")
                self.stats_labels['active_opportunities'].setText(f"{total_active:,}")
                self.stats_labels['completed_opportunities'].setText(f"{total_completed:,}")
                
                # Format response time more readably
                if avg_response_time > 24:
                    days = int(avg_response_time / 24)
                    hours = int(avg_response_time % 24)
                    self.stats_labels['avg_response_time'].setText(f"{days:,}d {hours}h")
                else:
                    self.stats_labels['avg_response_time'].setText(f"{avg_response_time:.1f} hours")
                
                # Update last login and account creation time if available
                if self.current_user.last_login:
                    self.stats_labels['last_login'].setText(
                        self.current_user.last_login.strftime("%Y-%m-%d %H:%M:%S")
                    )
                if self.current_user.created_at:
                    self.stats_labels['account_created'].setText(
                        self.current_user.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    )
            except Exception as e:
                print(f"Error loading statistics: {str(e)}")
                print(traceback.format_exc())
                
    def save_changes(self) -> None:
        """Save changes to the user profile"""
        with SessionLocal() as db:
            try:
                # Get and validate PIN fields
                current_pin = self.current_pin.text()
                new_pin = self.new_pin.text()
                
                # Validate current PIN
                if current_pin:
                    if not hash_pin(current_pin) == self.current_user.pin:
                        QMessageBox.warning(self, "Error", "Current PIN is incorrect")
                        return
                    
                    # Update PIN
                    self.current_user.pin = hash_pin(new_pin)
                
                # Get and validate other fields
                department_field = self.fields.get("department", {}).get("field")
                department_value: str = ""
                if isinstance(department_field, QComboBox):
                    department_value = department_field.currentText()
                elif isinstance(department_field, QLineEdit):
                    department_value = department_field.text()
                
                # Update user fields
                self.current_user.department = department_value
                
                # Commit changes
                db.commit()
                print("Profile updated successfully")
                
                QMessageBox.information(self, "Success", "Profile updated successfully")
                self.profile_updated.emit()
                print("Profile updated signal emitted")
                
            except Exception as e:
                print(f"Error saving changes: {str(e)}\nTraceback: {traceback.format_exc()}")
                db.rollback()
                QMessageBox.warning(self, "Error", "Failed to update profile")
            