from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QFormLayout, QFrame,
                           QMessageBox, QScrollArea, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from app.database.connection import SessionLocal
from app.models.models import User, Opportunity
from app.auth.auth_handler import hash_pin
from datetime import datetime, timedelta

class ProfileWidget(QWidget):
    profile_updated = pyqtSignal()
    
    def __init__(self, current_user):
        super().__init__()
        self.current_user = current_user
        self.initUI()
        
    def closeEvent(self, event):
        # Hide instead of close
        event.ignore()
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
        self.fields = {}
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
            if len(extra) > 0 and isinstance(extra[0], list):  # Combo box
                field = QComboBox()
                field.addItems(extra[0])
                field.setCurrentText(getattr(self.current_user, field_id))
                field.setEnabled(not readonly)
            else:  # Line edit
                field = QLineEdit()
                field.setText(str(getattr(self.current_user, field_id)))
                field.setReadOnly(readonly)
            
            self.fields[field_id] = field
            form_layout.addRow(label, field)
            
        # Add PIN change section
        pin_section = QFrame()
        pin_section.setStyleSheet(info_frame.styleSheet())
        pin_layout = QVBoxLayout()
        
        pin_title = QLabel("Change PIN")
        pin_title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        pin_layout.addWidget(pin_title)
        
        pin_form = QFormLayout()
        self.current_pin = QLineEdit()
        self.current_pin.setEchoMode(QLineEdit.Password)
        self.new_pin = QLineEdit()
        self.new_pin.setEchoMode(QLineEdit.Password)
        self.confirm_pin = QLineEdit()
        self.confirm_pin.setEchoMode(QLineEdit.Password)
        
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
        self.stats_labels = {}
        stats_configs = [
            ("total_opportunities", "Total Opportunities Created:"),
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
        
    def load_statistics(self):
        """Load user statistics"""
        db = SessionLocal()
        try:
            # Get opportunities statistics for both created and accepted opportunities
            created_opps = db.query(Opportunity).filter(
                Opportunity.creator_id == str(self.current_user.id)
            ).all()
            
            accepted_opps = db.query(Opportunity).filter(
                Opportunity.acceptor_id == str(self.current_user.id)
            ).all()
            
            # Combine opportunities while avoiding duplicates
            all_opps = list({opp.id: opp for opp in created_opps + accepted_opps}.values())
            
            total_opps = len(all_opps)
            active_opps = len([o for o in all_opps if o.status.lower() in ["new", "in progress"]])
            completed_opps = len([o for o in all_opps if o.status.lower() == "completed"])
            
            # Calculate average response time for completed opportunities
            response_times = []
            for opp in all_opps:
                if opp.status.lower() == "completed" and opp.completed_at and opp.created_at:
                    response_time = opp.completed_at - opp.created_at
                    response_times.append(response_time)
            
            if response_times:
                avg_response = sum(response_times, timedelta()) / len(response_times)
                # Format the response time nicely
                days = avg_response.days
                hours = avg_response.seconds // 3600
                minutes = (avg_response.seconds % 3600) // 60
                if days > 0:
                    avg_response_text = f"{days}d {hours}h"
                else:
                    avg_response_text = f"{hours}h {minutes}m"
            else:
                avg_response_text = "N/A"
            
            # Update statistics labels
            self.stats_labels["total_opportunities"].setText(str(total_opps))
            self.stats_labels["active_opportunities"].setText(str(active_opps))
            self.stats_labels["completed_opportunities"].setText(str(completed_opps))
            self.stats_labels["avg_response_time"].setText(avg_response_text)
            self.stats_labels["last_login"].setText(
                self.current_user.last_login.strftime("%Y-%m-%d %H:%M") if self.current_user.last_login else "Never"
            )
            self.stats_labels["account_created"].setText(
                self.current_user.created_at.strftime("%Y-%m-%d %H:%M") if self.current_user.created_at else "Unknown"
            )
            
            # Style statistics labels
            for label in self.stats_labels.values():
                label.setStyleSheet("""
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    margin-bottom: 10px;
                """)
                
        finally:
            db.close()
            
    def save_changes(self):
        """Save user profile changes"""
        print("Starting save_changes process...")  # Debug print
        db = None
        try:
            # Validate PIN change if attempted
            if self.current_pin.text() or self.new_pin.text() or self.confirm_pin.text():
                if not all([self.current_pin.text(), self.new_pin.text(), self.confirm_pin.text()]):
                    QMessageBox.warning(self, "Error", "Please fill in all PIN fields to change PIN")
                    return
                    
                if self.new_pin.text() != self.confirm_pin.text():
                    QMessageBox.warning(self, "Error", "New PINs do not match")
                    return
                    
                if hash_pin(self.current_pin.text()) != self.current_user.pin:
                    QMessageBox.warning(self, "Error", "Current PIN is incorrect")
                    return
            
            print("Opening database connection...")  # Debug print
            db = SessionLocal()
            
            print("Querying user...")  # Debug print
            user = db.query(User).filter(User.id == self.current_user.id).first()
            if not user:
                raise ValueError("User not found in database")
            
            # Update regular fields
            print("Updating regular fields...")  # Debug print
            for field_id, widget in self.fields.items():
                try:
                    if isinstance(widget, QLineEdit) and not widget.isReadOnly():
                        setattr(user, field_id, widget.text())
                    elif isinstance(widget, QComboBox):
                        setattr(user, field_id, widget.currentText())
                except Exception as field_error:
                    print(f"Error updating field {field_id}: {str(field_error)}")
                    raise
            
            # Update PIN if changed
            if self.new_pin.text():
                print("Updating PIN...")  # Debug print
                user.pin = hash_pin(self.new_pin.text())
            
            # Update icon theme preference - handle separately from fields
            print("Updating theme preference...")  # Debug print
            try:
                old_theme = user.icon_theme
                selected_theme = self.color_theme.currentText()
                print(f"Changing theme from {old_theme} to {selected_theme}")  # Debug print
                user.icon_theme = selected_theme
            except Exception as theme_error:
                print(f"Error updating theme: {str(theme_error)}")
                raise
            
            print("Setting updated_at timestamp...")  # Debug print
            user.updated_at = datetime.utcnow()
            
            print("Committing changes to database...")  # Debug print
            db.commit()
            
            print("Showing success message...")  # Debug print
            QMessageBox.information(self, "Success", "Profile updated successfully!")
            
            print("Emitting profile_updated signal...")  # Debug print
            self.profile_updated.emit()
            
            print("Hiding profile window...")  # Debug print
            self.hide()
            
        except Exception as e:
            print(f"Profile update failed: {str(e)}")
            if db:
                print("Rolling back database changes...")  # Debug print
                db.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update profile: {str(e)}\n\nPlease try again or contact support if the issue persists.")
        finally:
            if db:
                print("Closing database connection...")  # Debug print
                db.close()
            
    def showEvent(self, event):
        """Update statistics when the profile is shown"""
        super().showEvent(event)
        self.load_statistics()
            