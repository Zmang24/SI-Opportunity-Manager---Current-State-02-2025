from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QTextEdit, QPushButton, QComboBox,
                           QFileDialog, QMessageBox, QScrollArea, QFrame,
                           QCheckBox, QGroupBox, QDialog, QFormLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from app.database.connection import SessionLocal
from app.models.models import Opportunity, Vehicle, AdasSystem, File, User, Notification
from app.config import STORAGE_DIR
import os
import mimetypes
from datetime import datetime
import shutil
import hashlib
from app.services.supabase_storage import SupabaseStorageService

def calculate_file_hash(file_path):
    """Calculate SHA-256 hash of a file"""
    return SupabaseStorageService.calculate_file_hash(file_path)

def store_file(source_path, file_hash):
    """Store file in Supabase storage with hash-based name"""
    return SupabaseStorageService.store_file(source_path, file_hash)

class CustomVehicleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = parent.current_user if parent else None
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Add Custom Vehicle")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Warning message
        warning = QLabel(
            "Please verify that this is a valid Year, Make, and Model combination.\n"
            "This entry will be available to all users of the application."
        )
        warning.setStyleSheet("""
            color: #ffd700;
            font-size: 12px;
            margin-bottom: 15px;
            padding: 10px;
            background-color: rgba(255, 215, 0, 0.1);
            border-radius: 4px;
        """)
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        # Form layout
        form = QFormLayout()
        form.setSpacing(10)
        
        # Input fields
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("Enter year (e.g., 2024)")
        self.year_input.setStyleSheet("""
            QLineEdit {
                background-color: #3d3d3d;
                color: white;
                padding: 8px;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
        """)
        
        self.make_input = QLineEdit()
        self.make_input.setPlaceholderText("Enter make (e.g., Toyota)")
        self.make_input.setStyleSheet(self.year_input.styleSheet())
        
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("Enter model (e.g., Camry)")
        self.model_input.setStyleSheet(self.year_input.styleSheet())
        
        # Notes field
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Enter any notes about this vehicle (optional)")
        self.notes_input.setStyleSheet("""
            QTextEdit {
                background-color: #3d3d3d;
                color: white;
                padding: 8px;
                border: 1px solid #555555;
                border-radius: 4px;
                font-size: 14px;
                min-height: 60px;
            }
            QTextEdit:focus {
                border: 1px solid #0078d4;
            }
        """)
        
        # Add fields to form
        form.addRow("Year:", self.year_input)
        form.addRow("Make:", self.make_input)
        form.addRow("Model:", self.model_input)
        form.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.confirm_save_vehicle)
        save_btn.setStyleSheet("""
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
        
        button_layout.addWidget(save_btn)
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
        self.setWindowTitle("Add Custom Vehicle")
        self.setFixedSize(400, 500)
        
    def confirm_save_vehicle(self):
        """Show confirmation dialog before saving"""
        # Validate inputs first
        year = self.year_input.text().strip()
        make = self.make_input.text().strip()
        model = self.model_input.text().strip()
        
        if not all([year, make, model]):
            QMessageBox.warning(self, "Error", "Please fill in all required fields")
            return
            
        try:
            # Validate year is a number
            year_num = int(year)
            if year_num < 1900 or year_num > 2100:
                raise ValueError("Invalid year range")
                
            # Show confirmation dialog
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setText("Please confirm the vehicle details:")
            msg.setInformativeText(
                f"Year: {year}\n"
                f"Make: {make}\n"
                f"Model: {model}\n\n"
                "This entry will be available to all users.\n"
                "Are you sure these details are correct?"
            )
            msg.setWindowTitle("Confirm Vehicle Details")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            
            # Style the dialog
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b2b;
                    color: white;
                }
                QMessageBox QLabel {
                    color: white;
                    font-size: 12px;
                }
                QMessageBox QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    min-width: 80px;
                    font-weight: bold;
                }
                QMessageBox QPushButton:hover {
                    background-color: #106ebe;
                }
                QMessageBox QPushButton:pressed {
                    background-color: #005a9e;
                }
            """)
            
            if msg.exec_() == QMessageBox.Yes:
                self.save_vehicle()
                
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter a valid year between 1900 and 2100")
        
    def save_vehicle(self):
        """Save the vehicle to database"""
        try:
            db = SessionLocal()
            
            # Check if vehicle already exists
            existing = db.query(Vehicle).filter(
                Vehicle.year == self.year_input.text().strip(),
                Vehicle.make == self.make_input.text().strip(),
                Vehicle.model == self.model_input.text().strip()
            ).first()
            
            if existing:
                QMessageBox.warning(self, "Error", "This vehicle already exists in the database")
                return
            
            # Create new vehicle
            new_vehicle = Vehicle(
                year=self.year_input.text().strip(),
                make=self.make_input.text().strip(),
                model=self.model_input.text().strip(),
                notes=self.notes_input.toPlainText().strip(),
                is_custom=True,
                created_at=datetime.utcnow(),
                created_by_id=self.current_user.id if self.current_user else None
            )
            
            db.add(new_vehicle)
            db.commit()
            
            QMessageBox.information(self, "Success", "Vehicle added successfully!")
            self.accept()
            
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save vehicle: {str(e)}")
        finally:
            db.close()

class OpportunityForm(QWidget):
    # Add signal for new opportunity
    opportunity_created = pyqtSignal(object)  # Signal to emit when new opportunity is created

    # Define checkbox style as a class variable
    checkbox_style = """
        QCheckBox {
            color: #ffffff;
            spacing: 5px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
        }
        QCheckBox::indicator:unchecked {
            background-color: #3d3d3d;
            border: 1px solid #555555;
            border-radius: 3px;
        }
        QCheckBox::indicator:checked {
            background-color: #0078d4;
            border: 1px solid #0078d4;
            border-radius: 3px;
        }
    """

    def __init__(self, current_user_id):
        super().__init__()
        self.current_user_id = current_user_id  # Store the user ID
        self.current_user = None  # Will be loaded from database
        self.vehicles = []  # Initialize vehicles list
        self.ticket_number = None  # Store the generated ticket number
        self.load_current_user()  # Load the current user object
        self.initUI()
        
    def load_current_user(self):
        """Load the current user object from database"""
        try:
            db = SessionLocal()
            self.current_user = db.query(User).filter(User.id == self.current_user_id).first()
        except Exception as e:
            print(f"Error loading current user: {str(e)}")
        finally:
            db.close()
        
    def closeEvent(self, event):
        # Hide the window instead of closing it
        event.ignore()
        self.hide()
        
    def generate_ticket_number(self):
        """Generate a unique ticket number based on the current count of opportunities"""
        db = SessionLocal()
        try:
            # Get the current count of opportunities
            count = db.query(Opportunity).count()
            # Generate ticket number in format SI-YYYY-XXXXX where XXXXX is padded with zeros
            year = datetime.now().year
            ticket_number = f"SI-{year}-{(count + 1):05d}"
            return ticket_number
        finally:
            db.close()
            
    def initUI(self):
        # Main layout with scroll area
        main_layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #2b2b2b;
                border: none;
            }
        """)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        
        # Title
        title_label = QLabel("New Opportunity")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Ticket number display
        ticket_group = QGroupBox("Ticket Number")
        ticket_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
        """)
        ticket_layout = QVBoxLayout()
        
        self.ticket_label = QLabel()
        self.ticket_label.setStyleSheet("""
            QLabel {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #555555;
                border-radius: 3px;
                font-family: monospace;
                font-size: 14px;
            }
        """)
        ticket_layout.addWidget(self.ticket_label)
        ticket_group.setLayout(ticket_layout)
        layout.addWidget(ticket_group)
        
        # Generate and display the ticket number
        self.ticket_number = self.generate_ticket_number()
        self.ticket_label.setText(self.ticket_number)
        
        # Vehicle selection group
        vehicle_group = QGroupBox("Vehicle Information")
        vehicle_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        vehicle_layout = QHBoxLayout()
        
        # Create and style combo boxes
        combo_style = """
            QComboBox {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
                border-radius: 3px;
                min-width: 150px;
            }
            QComboBox:hover {
                border: 1px solid #666666;
            }
            QComboBox QAbstractItemView {
                background-color: #3d3d3d;
                color: #ffffff;
                selection-background-color: #555555;
            }
        """
        
        self.year_combo = QComboBox()
        self.year_combo.setStyleSheet(combo_style)
        self.make_combo = QComboBox()
        self.make_combo.setStyleSheet(combo_style)
        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(combo_style)
        
        # Connect signals for cascading updates
        self.year_combo.currentTextChanged.connect(self.update_makes)
        self.make_combo.currentTextChanged.connect(self.update_models)
        
        # Add labels and combos to layout
        for label_text, combo in [
            ("Year:", self.year_combo),
            ("Make:", self.make_combo),
            ("Model:", self.model_combo)
        ]:
            label = QLabel(label_text)
            label.setStyleSheet("color: #ffffff;")
            vehicle_layout.addWidget(label)
            vehicle_layout.addWidget(combo)
            vehicle_layout.addSpacing(10)
            
        # Add custom vehicle button
        add_custom_btn = QPushButton("+")
        add_custom_btn.setToolTip("Add Custom Vehicle")
        add_custom_btn.clicked.connect(self.show_custom_vehicle_dialog)
        add_custom_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        vehicle_layout.addWidget(add_custom_btn)
            
        vehicle_group.setLayout(vehicle_layout)
        layout.addWidget(vehicle_group)
        
        # Systems selection
        systems_group = QGroupBox("ADAS Systems")
        systems_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
        """)
        self.systems_layout = QVBoxLayout()
        
        # List to keep track of system rows
        self.system_rows = []
        
        # Add initial system row
        self.add_system_row()
        
        # Add button for new system
        add_system_btn = QPushButton("Add System")
        add_system_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 8px 16px;
                max-width: 120px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        add_system_btn.clicked.connect(self.add_system_row)
        self.systems_layout.addWidget(add_system_btn, alignment=Qt.AlignRight)
        
        systems_group.setLayout(self.systems_layout)
        layout.addWidget(systems_group)
        
        # Add file attachments section before description
        attachments_group = QGroupBox("Attachments")
        attachments_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
        """)
        attachments_layout = QVBoxLayout()
        
        # List to store attachments
        self.attachments = []
        self.attachment_labels = []
        
        # Add file button
        add_file_btn = QPushButton("Add File")
        add_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        add_file_btn.clicked.connect(self.add_attachment)
        attachments_layout.addWidget(add_file_btn)
        
        # Container for attachment labels
        self.attachments_container = QWidget()
        self.attachments_container_layout = QVBoxLayout(self.attachments_container)
        attachments_layout.addWidget(self.attachments_container)
        
        attachments_group.setLayout(attachments_layout)
        layout.addWidget(attachments_group)
        
        # Description
        desc_group = QGroupBox("Description")
        desc_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
        """)
        desc_layout = QVBoxLayout()
        
        self.description = QTextEdit()
        self.description.setStyleSheet("""
            QTextEdit {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px;
            }
        """)
        self.description.setMinimumHeight(100)
        desc_layout.addWidget(self.description)
        
        desc_group.setLayout(desc_layout)
        layout.addWidget(desc_group)
        
        # Submit button
        submit_btn = QPushButton("Submit")
        submit_btn.clicked.connect(self.submit_opportunity)
        submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        layout.addWidget(submit_btn, alignment=Qt.AlignCenter)
        
        # Set up scroll area
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        self.setLayout(main_layout)
        
        # Set window properties
        self.setWindowTitle("New Opportunity")
        self.setMinimumSize(800, 600)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
        """)
        
        # Load initial data
        self.load_data()
        
    def load_data(self):
        """Load vehicle and system data from database"""
        db = SessionLocal()
        try:
            # Load vehicles
            self.vehicles = db.query(Vehicle).all()  # Store vehicles in instance variable
            
            if self.vehicles:
                # Populate year combo
                years = sorted(set(v.year for v in self.vehicles), reverse=True)
                # Add 2025 if not already in the list
                if "2025" not in years:
                    years = ["2025"] + years
                # Add empty item at the start
                self.year_combo.addItem("")
                self.year_combo.addItems(map(str, years))
            else:
                print("No vehicles found in database")
            
        except Exception as e:
            print(f"Error loading data: {str(e)}")
        finally:
            db.close()
            
    def update_makes(self, year):
        """Update makes combo box based on selected year"""
        self.make_combo.clear()
        if year and self.vehicles:
            makes = sorted(set(v.make for v in self.vehicles if str(v.year) == year))
            self.make_combo.addItems(makes)
            # Trigger initial model update if there are makes
            if makes:
                self.update_models(makes[0])
            
    def update_models(self, make):
        """Update models combo box based on selected make"""
        self.model_combo.clear()
        year = self.year_combo.currentText()
        if year and make and self.vehicles:
            models = sorted(set(v.model for v in self.vehicles 
                              if str(v.year) == year and v.make == make))
            self.model_combo.addItems(models)
            
    def add_system_row(self):
        """Add a new system row with dropdown and affected portions"""
        row_widget = QWidget()
        row_layout = QVBoxLayout(row_widget)
        
        # System selection
        system_header = QHBoxLayout()
        
        # System dropdown
        system_combo = QComboBox()
        system_combo.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #555555;
                border-radius: 3px;
                min-width: 300px;
            }
            QComboBox:hover {
                border: 1px solid #666666;
            }
            QComboBox QAbstractItemView {
                background-color: #3d3d3d;
                color: #ffffff;
                selection-background-color: #555555;
            }
        """)
        
        # Remove button (except for first row)
        if self.system_rows:
            remove_btn = QPushButton("×")
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d83b01;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    min-width: 30px;
                    max-width: 30px;
                    min-height: 30px;
                    max-height: 30px;
                }
                QPushButton:hover {
                    background-color: #ea4a1f;
                }
            """)
            remove_btn.clicked.connect(lambda: self.remove_system_row(row_widget))
            system_header.addWidget(remove_btn)
        
        system_header.addWidget(system_combo)
        row_layout.addLayout(system_header)
        
        # Affected Portions for this system
        portions_group = QGroupBox("Affected Portions")
        portions_group.setStyleSheet("""
            QGroupBox {
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 5px;
                padding: 10px;
            }
        """)
        portions_layout = QVBoxLayout()
        
        portions_checkboxes = {}
        portions = [
            "R&I",
            "Calibration Procedure",
            "Justification",
            "Full Document Missing",
            "Highlighting Issue",
            "Naming Issue"
        ]
        
        for portion in portions:
            checkbox = QCheckBox(portion)
            checkbox.setStyleSheet(self.checkbox_style)
            # Ensure ampersand is displayed as text, not as a shortcut
            if portion == "R&I":
                checkbox.setText("R&&I")  # Double ampersand to escape it
            portions_checkboxes[portion] = checkbox
            portions_layout.addWidget(checkbox)
            
        portions_group.setLayout(portions_layout)
        row_layout.addWidget(portions_group)
        
        # Add to systems layout
        self.systems_layout.insertWidget(len(self.system_rows), row_widget)
        
        # Store row data
        row_data = {
            'widget': row_widget,
            'combo': system_combo,
            'portions': portions_checkboxes
        }
        self.system_rows.append(row_data)
        
        # Load systems into combo
        db = SessionLocal()
        try:
            systems = db.query(AdasSystem).all()
            if systems:
                system_combo.addItems([f"{s.code} - {s.name}" for s in systems])
        finally:
            db.close()

    def remove_system_row(self, row_widget):
        """Remove a system row"""
        # Find and remove row data
        for row_data in self.system_rows:
            if row_data['widget'] == row_widget:
                self.system_rows.remove(row_data)
                break
        
        # Remove widget
        row_widget.deleteLater()

    def add_attachment(self):
        """Handle file attachment"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "All Files (*.*)"
        )
        
        if file_path:
            try:
                # Calculate file hash
                file_hash = calculate_file_hash(file_path)
                
                # Store file
                storage_path = store_file(file_path, file_hash)
                
                # Create container for attachment row
                attachment_row = QWidget()
                row_layout = QHBoxLayout(attachment_row)
                
                # Add file name label
                file_name = os.path.basename(file_path)
                label = QLabel(file_name)
                label.setStyleSheet("color: #ffffff;")
                row_layout.addWidget(label)
                
                # Add remove button
                remove_btn = QPushButton("×")
                remove_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #d83b01;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-weight: bold;
                        min-width: 24px;
                        max-width: 24px;
                    }
                    QPushButton:hover {
                        background-color: #ea4a1f;
                    }
                """)
                remove_btn.clicked.connect(lambda: self.remove_attachment(attachment_row, file_path))
                row_layout.addWidget(remove_btn)
                
                # Add to container
                self.attachments_container_layout.addWidget(attachment_row)
                
                # Store file info
                self.attachments.append({
                    'path': file_path,
                    'storage_path': storage_path,
                    'hash': file_hash,
                    'name': file_name,
                    'size': os.path.getsize(file_path),
                    'mime_type': mimetypes.guess_type(file_path)[0]
                })
                self.attachment_labels.append(attachment_row)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to attach file: {str(e)}")

    def remove_attachment(self, row_widget, file_path):
        """Remove an attachment"""
        index = self.attachments.index(file_path)
        self.attachments.pop(index)
        self.attachment_labels.pop(index)
        row_widget.deleteLater()

    def submit_opportunity(self):
        if not self.validate_form():
            return
            
        db = SessionLocal()
        try:
            # Get selected systems and their affected portions
            systems_data = []
            for row in self.system_rows:
                system_text = row['combo'].currentText()
                if system_text:
                    system_code = system_text.split(' - ')[0]
                    affected_portions = [
                        portion for portion, checkbox in row['portions'].items()
                        if checkbox.isChecked()
                    ]
                    if affected_portions:  # Only add if portions are selected
                        systems_data.append({
                            'system': system_code,
                            'affected_portions': affected_portions
                        })
            
            # Create the opportunity
            new_opp = Opportunity(
                title=self.ticket_number,
                year=self.year_combo.currentText(),
                make=self.make_combo.currentText(),
                model=self.model_combo.currentText(),
                description=self.description.toPlainText(),
                status='new',
                systems=systems_data,
                creator_id=self.current_user_id,
                created_at=datetime.utcnow()
            )
            
            db.add(new_opp)
            db.flush()  # Get the ID without committing
            
            # Create notifications for all users except the creator
            all_users = db.query(User).filter(User.id != self.current_user_id).all()
            for user in all_users:
                notification = Notification(
                    user_id=user.id,
                    opportunity_id=new_opp.id,
                    type="new_opportunity",
                    message=f"New opportunity created: {new_opp.title} - {new_opp.display_title}",
                    created_at=datetime.utcnow(),
                    read=False
                )
                db.add(notification)
            
            # Handle file attachments
            for attachment in self.attachments:
                file_attachment = File(
                    opportunity_id=new_opp.id,
                    uploader_id=self.current_user_id,
                    name=attachment['name'],
                    original_name=attachment['name'],
                    storage_path=attachment['storage_path'],
                    size=attachment['size'],
                    mime_type=attachment['mime_type'],
                    hash=attachment['hash'],
                    created_at=datetime.utcnow()
                )
                db.add(file_attachment)
            
            db.commit()
            
            # Emit signal with the new opportunity
            self.opportunity_created.emit(new_opp)
            
            QMessageBox.information(self, "Success", "Opportunity created successfully!")
            self.clear_form()
            
        except Exception as e:
            db.rollback()
            QMessageBox.critical(self, "Error", f"Failed to create opportunity: {str(e)}")
        finally:
            db.close()
            
    def validate_form(self):
        """Modified validation to remove title check since we're using auto-generated ticket numbers"""
        if not all([self.year_combo.currentText(),
                   self.make_combo.currentText(),
                   self.model_combo.currentText()]):
            QMessageBox.warning(self, "Validation Error", "Please select a complete vehicle!")
            return False
            
        if not self.description.toPlainText():
            QMessageBox.warning(self, "Validation Error", "Please enter a description!")
            return False
            
        # Validate at least one system with affected portions
        valid_system = False
        for row in self.system_rows:
            if row['combo'].currentText() and any(checkbox.isChecked() for checkbox in row['portions'].values()):
                valid_system = True
                break
                
        if not valid_system:
            QMessageBox.warning(self, "Validation Error", "Please select at least one system with affected portions!")
            return False
            
        return True
        
    def clear_form(self):
        # Generate new ticket number
        self.ticket_number = self.generate_ticket_number()
        self.ticket_label.setText(self.ticket_number)
        
        self.year_combo.setCurrentIndex(0)
        self.make_combo.clear()
        self.model_combo.clear()
        self.description.clear()
        
        # Clear attachments
        for label in self.attachment_labels:
            label.deleteLater()
        self.attachments = []
        self.attachment_labels = []
        
        # Remove all system rows except the first
        while len(self.system_rows) > 1:
            row_data = self.system_rows[-1]
            self.remove_system_row(row_data['widget'])
            
        # Clear first row
        if self.system_rows:
            first_row = self.system_rows[0]
            first_row['combo'].setCurrentIndex(0)
            for checkbox in first_row['portions'].values():
                checkbox.setChecked(False)

    def show_custom_vehicle_dialog(self):
        """Show dialog to add custom vehicle"""
        dialog = CustomVehicleDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Refresh vehicle data
            self.load_data()
            
            # Select the newly added vehicle
            if self.vehicles:
                latest_vehicle = self.vehicles[-1]
                self.year_combo.setCurrentText(latest_vehicle.year)
                self.make_combo.setCurrentText(latest_vehicle.make)
                self.model_combo.setCurrentText(latest_vehicle.model) 