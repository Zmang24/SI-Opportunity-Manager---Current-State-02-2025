from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QScrollArea, QFrame, QMessageBox, QComboBox, QDateEdit,
                           QDialog, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, QDate, QPoint, QRect
from PyQt5.QtGui import QCloseEvent, QKeySequence, QPainter, QPixmap, QColor
from app.database.connection import SessionLocal
from app.models.models import Opportunity, Notification, ActivityLog, User
from app.config import STORAGE_DIR
import os
import traceback
from datetime import datetime, timezone, timedelta
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal, QEvent
from typing import Dict, List, Optional, Union, Any, cast, TypeVar, Iterable
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from sqlalchemy import Column, ColumnElement, String, DateTime, Interval
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.expression import cast as sql_cast
from sqlalchemy import text
import math  # Add this import at the top

T = TypeVar('T')

class DebugDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dashboard Debug Information")
        self.setMinimumSize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
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
        
        layout = QVBoxLayout()
        
        # Debug information text area
        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        layout.addWidget(self.debug_text)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)

class DashboardWidget(QWidget):
    refresh_needed = pyqtSignal()  # Signal to trigger refresh of other components
    
    def __init__(self, current_user: Optional[User] = None):
        super().__init__()
        self.current_user = current_user
        self.current_filter: str = "new"
        self.opportunity_widgets: Dict[str, QFrame] = {}  # Change to dict to store by ID
        self.is_loading: bool = False
        self.is_compact: bool = True
        self.refresh_timer = QTimer()
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.do_refresh)
        self.debug_dialog = None
        # Get local timezone for display
        self.local_timezone = self.get_local_timezone()
        # Add refresh animation properties
        self.refresh_animation = None
        self.refresh_message = None
        self.spinner_angle = 0
        self.spinner_timer = QTimer()
        self.spinner_timer.timeout.connect(self.update_spinner)
        self.fade_timer = QTimer()
        self.fade_timer.timeout.connect(self.fade_message)
        self.fade_opacity = 1.0
        
        self.initUI()
        
        # Set initial window size
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.5), int(screen.height() * 0.6))  # Slightly smaller default size
        
    def get_local_timezone(self) -> ZoneInfo:
        """Get the local timezone from the system"""
        try:
            # Try to get the system's timezone
            local_tz_name = datetime.now().astimezone().tzinfo.tzname(None)
            
            # If we have a valid timezone name, use it
            if local_tz_name:
                try:
                    return ZoneInfo(local_tz_name)
                except Exception:
                    # If the name is not in the ZoneInfo database, try to map common names
                    tz_mapping = {
                        "Eastern Standard Time": "America/New_York",
                        "Central Standard Time": "America/Chicago", 
                        "Mountain Standard Time": "America/Denver",
                        "Pacific Standard Time": "America/Los_Angeles",
                        "GMT Standard Time": "Europe/London"
                    }
                    if local_tz_name in tz_mapping:
                        return ZoneInfo(tz_mapping[local_tz_name])
            
            # Fallbacks
            # Try getting TZ environment variable
            if 'TZ' in os.environ:
                try:
                    return ZoneInfo(os.environ['TZ'])
                except Exception:
                    pass
                    
            print(f"Using system timezone detection: {local_tz_name}")
            # Fallback to UTC if all else fails
            return ZoneInfo('UTC')
        except Exception as e:
            print(f"Error detecting timezone: {e}")
            return ZoneInfo('UTC')
    
    def convert_to_local_time(self, utc_time: datetime) -> datetime:
        """Convert UTC timestamp to local timezone for display"""
        if not utc_time:
            return utc_time
            
        # Ensure the datetime has timezone info
        if utc_time.tzinfo is None:
            # If no timezone, assume it's UTC
            utc_time = utc_time.replace(tzinfo=ZoneInfo('UTC'))
        
        # Convert to local timezone
        return utc_time.astimezone(self.local_timezone)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_5 and event.modifiers() == Qt.ControlModifier:
            self.show_debug_dialog()
        else:
            super().keyPressEvent(event)
            
    def show_debug_dialog(self):
        """Show debug dialog with current state information"""
        if not self.debug_dialog:
            self.debug_dialog = DebugDialog(self)
            
        debug_info = []
        
        # Dependencies check
        debug_info.append("=== Dependencies Check ===")
        try:
            import pkg_resources
            required_packages = {
                'PyQt5': '5.15.0',
                'SQLAlchemy': '1.4.0',
                'psycopg2-binary': '2.9.0',
                'python-dotenv': '0.19.0',
                'pandas': '1.3.0',
                'numpy': '1.21.0',
                'openpyxl': '3.0.0',
                'requests': '2.26.0',
                'Pillow': '8.3.0',
                'python-dateutil': '2.8.2'
            }
            
            for package, min_version in required_packages.items():
                try:
                    version = pkg_resources.get_distribution(package).version
                    debug_info.append(f"{package}: {version} (Required: {min_version})")
                except pkg_resources.DistributionNotFound:
                    debug_info.append(f"❌ {package}: Not installed")
            
            # Check for zoneinfo (built-in module)
            try:
                import zoneinfo
                debug_info.append("zoneinfo: Built-in module (Python 3.9+)")
            except ImportError:
                debug_info.append("❌ zoneinfo: Not available (requires Python 3.9+)")
                
        except Exception as e:
            debug_info.append(f"Error checking dependencies: {str(e)}")
        
        # Database connection check
        debug_info.append("\n=== Database Connection Status ===")
        try:
            db = SessionLocal()
            # Test Neon connection using SQLAlchemy text()
            result = db.execute(text("SELECT version()")).scalar()
            debug_info.append(f"✅ Neon Database Connected")
            debug_info.append(f"PostgreSQL Version: {result}")
            
            # Test database tables
            tables = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).fetchall()
            debug_info.append("\nAvailable Tables:")
            for table in tables:
                debug_info.append(f"- {table[0]}")
            
            # Test opportunity table
            opp_count = db.query(Opportunity).count()
            debug_info.append(f"\nTotal Opportunities: {opp_count}")
            
        except Exception as e:
            debug_info.append(f"❌ Database Connection Error: {str(e)}")
            debug_info.append(traceback.format_exc())
        finally:
            if 'db' in locals():
                db.close()
        
        # Supabase connection check
        debug_info.append("\n=== Supabase Connection Status ===")
        try:
            from app.services.supabase_storage import SupabaseStorageService
            # Test Supabase connection
            if SupabaseStorageService.test_connection():
                debug_info.append("✅ Supabase Storage Connected")
                # List buckets if connection is successful
                buckets = SupabaseStorageService.list_buckets()
                if buckets:
                    debug_info.append("\nAvailable Buckets:")
                    for bucket in buckets:
                        debug_info.append(f"- {bucket}")
                else:
                    debug_info.append("\nNo buckets found in storage")
            else:
                debug_info.append("❌ Supabase Storage Connection Failed")
                debug_info.append("Unable to connect to Supabase storage service")
        except Exception as e:
            debug_info.append(f"❌ Supabase Error: {str(e)}")
            debug_info.append(traceback.format_exc())
        
        # Environment variables check
        debug_info.append("\n=== Environment Variables ===")
        required_env_vars = [
            'DATABASE_URL',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'SUPABASE_BUCKET'
        ]
        for var in required_env_vars:
            value = os.getenv(var, '')
            if value:
                # Mask sensitive information
                if 'key' in var.lower() or 'password' in var.lower() or 'secret' in var.lower():
                    masked_value = value[:4] + '****' + value[-4:] if len(value) > 8 else '****'
                elif '@' in value:  # For URLs with credentials
                    masked_value = value.replace(value.split('@')[-1], '****')
                else:
                    masked_value = value
                debug_info.append(f"✅ {var}: {masked_value}")
            else:
                debug_info.append(f"❌ {var}: Not set")
        
        # Current application state
        debug_info.append("\n=== Application State ===")
        debug_info.append(f"Current Filter: {self.current_filter}")
        debug_info.append(f"Displayed Widgets: {len(self.opportunity_widgets)}")
        
        # User info
        if self.current_user:
            debug_info.append(f"\nCurrent User:")
            debug_info.append(f"ID: {self.current_user.id}")
            debug_info.append(f"Name: {self.current_user.first_name} {self.current_user.last_name}")
            debug_info.append(f"Role: {self.current_user.role}")
            debug_info.append(f"Team: {self.current_user.team}")
        
        # Recent errors
        if hasattr(self, '_last_error'):
            debug_info.append(f"\nLast Error: {self._last_error}")
        
        self.debug_dialog.debug_text.setText("\n".join(debug_info))
        self.debug_dialog.show()
        self.debug_dialog.raise_()
        self.debug_dialog.activateWindow()
        
    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle closing of the dashboard window and cleanup all resources"""
        try:
            # Clean up widgets
            self.cleanup_widgets()
            
            # Stop any running timers
            if hasattr(self, 'refresh_timer'):
                self.refresh_timer.stop()
            
            # Close database connections
            try:
                db = SessionLocal()
                db.close()
            except:
                pass
            
            # Hide the window instead of closing it
            event.ignore()
            self.hide()
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
            print(traceback.format_exc())
            event.ignore()  # Still ignore the event even if there's an error
        
    def cleanup_widgets(self) -> None:
        """Safely clean up widgets"""
        try:
            # Clear all widgets from the layout
            if hasattr(self, 'opportunities_layout'):
                while self.opportunities_layout.count():
                    item = self.opportunities_layout.takeAt(0)
                    if item and item.widget():
                        item.widget().deleteLater()
            
            # Clear the widget list
            self.opportunity_widgets.clear()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(16)
        
        # Title row with refresh and view toggle
        title_row = QHBoxLayout()
        title_row.setSpacing(16)
        
        title = QLabel("Dashboard")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
        """)
        title_row.addWidget(title)

        # Add view toggle button with clearer text
        self.view_toggle_btn = QPushButton("Compact View" if self.is_compact else "Expanded View")
        self.view_toggle_btn.setToolTip("Toggle between compact and expanded view")
        self.view_toggle_btn.clicked.connect(self.toggle_view_mode)
        self.view_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #0078d4;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #2196F3;
            }
        """)
        title_row.addWidget(self.view_toggle_btn)
        
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #0078d4;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #2196F3;
            }
        """)
        refresh_btn.clicked.connect(self.load_opportunities)
        title_row.addWidget(refresh_btn, alignment=Qt.AlignRight)
        header_layout.addLayout(title_row)
        
        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        
        filter_buttons = [
            ("All Tickets", "all"),
            ("My Tickets", "my_tickets"),
            ("New", "new"),
            ("In Progress", "in_progress"),
            ("Completed", "completed"),
            ("Needs Info", "needs_info")
        ]
        
        for label, filter_id in filter_buttons:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(filter_id == "new")  # Changed to check if filter is "new"
            btn.setProperty("filter_id", filter_id)
            btn.clicked.connect(lambda checked, f=filter_id: self.apply_filter(f))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #cccccc;
                    border: 1px solid #3d3d3d;
                    padding: 8px 16px;
                    border-radius: 16px;
                    font-size: 13px;
                }
                QPushButton:checked {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                }
                QPushButton:hover:!checked {
                    background-color: #2d2d2d;
                    border-color: #4d4d4d;
                }
            """)
            filter_row.addWidget(btn)
        
        filter_row.addStretch()
        header_layout.addLayout(filter_row)
        
        # Add advanced filter bar (initially hidden)
        self.advanced_filter_frame = QFrame()
        self.advanced_filter_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #666666;
            }
            QDateEdit {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 120px;
            }
            QDateEdit:hover {
                border-color: #666666;
            }
        """)
        
        advanced_filter_layout = QHBoxLayout(self.advanced_filter_frame)
        advanced_filter_layout.setSpacing(16)
        
        # Date range filter
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date Range:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))  # Default to 7 days ago
        date_layout.addWidget(self.date_from)
        date_layout.addWidget(QLabel("to"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_to)
        advanced_filter_layout.addLayout(date_layout)
        
        # Create container for My Tickets specific filters
        self.my_tickets_filters = QWidget()
        my_tickets_layout = QHBoxLayout(self.my_tickets_filters)
        my_tickets_layout.setSpacing(16)
        
        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.setStyleSheet("""
            QComboBox {
                background-color: #262626;
                color: white;
                border: 1px solid #404040;
                padding: 4px 8px;
                border-radius: 4px;
                min-width: 100px;
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
        """)
        self.status_filter.addItem("")  # Empty default option
        self.status_filter.addItem("All")
        self.status_filter.addItem("New")
        self.status_filter.addItem("In Progress")
        self.status_filter.addItem("Completed")
        self.status_filter.addItem("Needs Info")
        self.status_filter.currentTextChanged.connect(self.filter_opportunities)
        my_tickets_layout.addWidget(self.status_filter)
        
        # Assignment filter
        self.assignment_filter = QComboBox()
        self.assignment_filter.setStyleSheet("""
            QComboBox {
                background-color: #262626;
                color: white;
                border: 1px solid #404040;
                padding: 4px 8px;
                border-radius: 4px;
                min-width: 100px;
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
        """)
        self.assignment_filter.addItem("")  # Empty default option
        self.assignment_filter.addItem("All")
        self.assignment_filter.addItem("Created by me")
        self.assignment_filter.addItem("Assigned to me")
        self.assignment_filter.addItem("Unassigned")
        self.assignment_filter.currentTextChanged.connect(self.filter_opportunities)
        my_tickets_layout.addWidget(self.assignment_filter)
        
        advanced_filter_layout.addWidget(self.my_tickets_filters)
        
        # Apply filters button
        apply_btn = QPushButton("Apply Filters")
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        apply_btn.clicked.connect(self.apply_advanced_filters)
        advanced_filter_layout.addWidget(apply_btn)
        
        # Reset filters button
        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #d83b01;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ea4a1f;
            }
        """)
        reset_btn.clicked.connect(self.reset_filters)
        advanced_filter_layout.addWidget(reset_btn)
        
        advanced_filter_layout.addStretch()
        
        # Initially hide the advanced filter frame
        self.advanced_filter_frame.hide()
        layout.addWidget(self.advanced_filter_frame)
        
        layout.addLayout(header_layout)
        
        # Create scroll area for opportunities
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
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
        
        # Container for opportunities
        self.opportunities_container = QWidget()
        self.opportunities_container.setStyleSheet("background-color: transparent;")
        self.opportunities_layout = QVBoxLayout(self.opportunities_container)
        self.opportunities_layout.setSpacing(16)
        self.opportunities_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area.setWidget(self.opportunities_container)
        layout.addWidget(self.scroll_area)
        
        # Create refresh animation components (initially hidden)
        self.refresh_animation = QLabel(self)
        self.refresh_animation.setFixedSize(40, 40)
        self.refresh_animation.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 20px;
            }
        """)
        self.refresh_animation.hide()
        
        self.refresh_message = QLabel("Refreshing...", self)
        self.refresh_message.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-size: 14px;
                font-weight: bold;
                background-color: rgba(30, 30, 30, 220);
                border-radius: 4px;
                padding: 6px 10px;
            }
        """)
        self.refresh_message.setAlignment(Qt.AlignCenter)
        self.refresh_message.adjustSize()
        self.refresh_message.hide()
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: #1e1e1e;")
        
        # Load initial opportunities
        self.load_opportunities()
        
    def apply_filter(self, filter_id):
        """Apply filter and reload opportunities"""
        # Update filter buttons visual state
        for button in self.findChildren(QPushButton):
            if hasattr(button, 'property') and button.property("filter_id"):
                button.setChecked(button.property("filter_id") == filter_id)
        
        self.current_filter = filter_id
        
        # Show/hide advanced filter frame and My Tickets specific filters
        self.advanced_filter_frame.setVisible(True)  # Always show advanced filter frame
        self.my_tickets_filters.setVisible(filter_id == "my_tickets")  # Only show My Tickets specific filters for my_tickets
        
        self.load_opportunities()

    def filter_opportunities(self):
        """Filter opportunities based on status and assignment filters"""
        self.load_opportunities()

    def apply_advanced_filters(self):
        """Apply advanced filters"""
        self.load_opportunities()

    def reset_filters(self):
        """Reset advanced filters to default values"""
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_to.setDate(QDate.currentDate())
        if self.current_filter == "my_tickets":
            self.status_filter.setCurrentText("")
            self.assignment_filter.setCurrentText("")
        self.apply_advanced_filters()

    def get_filtered_opportunities(self, db: Session) -> List[Opportunity]:
        """Get opportunities based on current filter and advanced filter settings"""
        query = db.query(Opportunity)
        
        # Base filters
        if self.current_filter == "new":
            query = query.filter(sql_cast(Opportunity.status, String).ilike("new"))
        elif self.current_filter == "in_progress":
            query = query.filter(sql_cast(Opportunity.status, String).ilike("in progress"))
        elif self.current_filter == "completed":
            query = query.filter(sql_cast(Opportunity.status, String).ilike("completed"))
        elif self.current_filter == "needs_info":
            query = query.filter(sql_cast(Opportunity.status, String).ilike("needs info"))
        elif self.current_filter == "my_tickets" and self.current_user:
            # Show tickets where user is either creator or acceptor
            query = query.filter(
                (Opportunity.creator_id == self.current_user.id) |
                (Opportunity.acceptor_id == self.current_user.id)
            )
            
            # Apply status filter if set
            if hasattr(self, 'status_filter') and self.status_filter.currentText() and self.status_filter.currentText() != "All":
                query = query.filter(sql_cast(Opportunity.status, String).ilike(self.status_filter.currentText().lower()))
                
            # Apply assignment filter if set
            if hasattr(self, 'assignment_filter') and self.assignment_filter.currentText():
                assignment = self.assignment_filter.currentText()
                if assignment == "Created by me":
                    query = query.filter(Opportunity.creator_id == self.current_user.id)
                elif assignment == "Assigned to me":
                    query = query.filter(Opportunity.acceptor_id == self.current_user.id)
                elif assignment == "Unassigned":
                    query = query.filter(Opportunity.acceptor_id.is_(None))
        
        # Apply date filters if they exist and are set
        if hasattr(self, 'date_from') and hasattr(self, 'date_to'):
            start_date = self.date_from.date().toPyDate()
            end_date = self.date_to.date().toPyDate()
            if start_date and end_date:
                utc = ZoneInfo('UTC')
                query = query.filter(
                    sql_cast(Opportunity.created_at, DateTime).between(
                        datetime.combine(start_date, datetime.min.time(), tzinfo=utc),
                        datetime.combine(end_date, datetime.max.time(), tzinfo=utc)
                    ))
        
        return query.order_by(Opportunity.created_at.desc()).all()

    def load_opportunities(self):
        """Load opportunities based on current filter"""
        if self.is_loading:
            return
            
        self.is_loading = True
        
        # Show refresh animation
        self.show_refresh_animation()
        
        try:
            # Clear existing widgets
            self.cleanup_widgets()
            
            db = SessionLocal()
            try:
                # Get opportunities based on filter
                opportunities = self.get_filtered_opportunities(db)
                
                print(f"DEBUG: DashboardWidget loaded {len(opportunities)} opportunities with filter '{self.current_filter}'")
                
                # Store last error if any
                self._last_error = None
                
                # Mark new opportunities as viewed and update toolbar
                # Important: This must be consistent with how the notification system identifies "new" tickets
                parent = self.parent()
                if parent and hasattr(parent, 'toolbar'):
                    marked_count = 0
                    
                    # Dump the current filter and all the statuses for debugging
                    print(f"\nDEBUG: Dashboard refresh showing filter '{self.current_filter}'")
                    status_counts = {}
                    for opp in opportunities:
                        status = opp.status.lower() if opp.status else "unknown"
                        status_counts[status] = status_counts.get(status, 0) + 1
                    print(f"DEBUG: Status distribution in refresh view: {status_counts}")
                    
                    # For all new status items visible in any view - case-insensitive
                    for opp in opportunities:
                        # Check status case-insensitively
                        if opp.status and opp.status.lower() == "new":
                            if opp.id not in parent.toolbar.viewed_opportunities:
                                print(f"DEBUG: Dashboard refresh marking opportunity as viewed: {opp.id} (Status: {opp.status}, Title: {opp.title})")
                                parent.toolbar.viewed_opportunities.add(opp.id)
                                marked_count += 1
                    
                    if marked_count > 0:
                        print(f"DEBUG: Dashboard refresh marked {marked_count} opportunities as viewed")
                        # Update notification badge
                        parent.toolbar.check_updates()
                
                # Add opportunity widgets
                for opportunity in opportunities:
                    self.add_opportunity_widget(opportunity)
                    
                # Update scroll area contents
                self.opportunities_container.adjustSize()
                
            except Exception as e:
                self._last_error = str(e)
                print(f"Error loading opportunities: {str(e)}")
                print(traceback.format_exc())
            finally:
                db.close()
                
        finally:
            self.is_loading = False
            # Hide spinner and show confirmation
            self.hide_refresh_animation()

    def do_refresh(self):
        """Actually perform the refresh"""
        if self.is_loading:
            return
            
        self.is_loading = True
        
        # Show refresh animation
        self.show_refresh_animation()
        
        db = SessionLocal()
        try:
            # Clear existing widgets
            self.cleanup_widgets()
            
            # Get opportunities based on filter
            opportunities = self.get_filtered_opportunities(db)
            
            print(f"DEBUG: DashboardWidget refreshed {len(opportunities)} opportunities with filter '{self.current_filter}'")
            
            # Mark new opportunities as viewed and update toolbar
            # Important: This must be consistent with how the notification system identifies "new" tickets
            parent = self.parent()
            if parent and hasattr(parent, 'toolbar'):
                marked_count = 0
                
                # For all new status items visible in any view
                for opp in opportunities:
                    # Check status case-insensitively
                    if opp.status and opp.status.lower() == "new":
                        if opp.id not in parent.toolbar.viewed_opportunities:
                            print(f"DEBUG: Dashboard marking opportunity as viewed: {opp.id} (Status: {opp.status})")
                            parent.toolbar.viewed_opportunities.add(opp.id)
                            marked_count += 1
                
                if marked_count > 0:
                    print(f"DEBUG: Dashboard marked {marked_count} opportunities as viewed")
                    # Update notification badge
                    parent.toolbar.check_updates()
            
            # Add opportunity widgets
            for opportunity in opportunities:
                self.add_opportunity_widget(opportunity)
                
            # Update scroll area contents
            self.opportunities_container.adjustSize()
            
        except Exception as e:
            print(f"Error refreshing opportunities: {str(e)}")
            import traceback
            print(traceback.format_exc())
        finally:
            self.is_loading = False
            db.close()
            
            # Hide spinner and show confirmation
            self.hide_refresh_animation()

    def add_opportunity_widget(self, opportunity: Opportunity) -> Optional[QFrame]:
        """Add a widget for displaying an opportunity"""
        try:
            card = QFrame()
            card.setObjectName(f"card_{opportunity.id}")
            
            # Store the widget in our dictionary
            self.opportunity_widgets[str(opportunity.id)] = card
            
            # Adjust card style based on view mode
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: #2d2d2d;
                    border-radius: {6 if self.is_compact else 8}px;
                    padding: {12 if self.is_compact else 20}px;
                }}
                QFrame:hover {{
                    background-color: #333333;
                }}
            """)
            
            card_layout = QVBoxLayout()
            card_layout.setSpacing(self.is_compact and 8 or 16)
            card_layout.setContentsMargins(0, 0, 0, 0)
            
            # Header section with title and status
            header = QHBoxLayout()
            header.setSpacing(self.is_compact and 8 or 16)
            
            # Title and submitter info
            title_section = QVBoxLayout()
            title_section.setSpacing(self.is_compact and 2 or 4)
            
            # Adjust title style based on view mode
            title = QLabel(f"{opportunity.display_title}")
            title.setStyleSheet(f"""
                color: #ffffff;
                font-size: {14 if self.is_compact else 18}px;
                font-weight: bold;
            """)
            title_section.addWidget(title)
            
            # Compact mode: combine ticket and submitter info
            if self.is_compact:
                # First line: Ticket ID and creator info
                info_text = f"{opportunity.title} • {opportunity.creator.first_name} {opportunity.creator.last_name}"
                if opportunity.creator.team:
                    info_text += f" ({opportunity.creator.team})"
                info = QLabel(info_text)
                info.setStyleSheet("color: #999999; font-size: 12px;")
                title_section.addWidget(info)

                # Second line: Timestamps and acceptor info
                time_info = QLabel()
                time_text = []
                
                # Add created time
                if opportunity.created_at:
                    # Convert to local time for display
                    local_created_time = self.convert_to_local_time(opportunity.created_at)
                    created_time = local_created_time.strftime("%Y-%m-%d %H:%M")
                    time_text.append(f"Created: {created_time}")
                
                # Add acceptor info if assigned
                if opportunity.acceptor_id:
                    acceptor = opportunity.acceptor
                    if opportunity.status.lower() == "completed" and opportunity.completed_at:
                        # Show both total time and work time for completed tickets
                        total_time = opportunity.response_time if opportunity.response_time else None
                        work_time = opportunity.work_time if opportunity.work_time else None
                        
                        # Convert completed time to local time
                        if opportunity.completed_at:
                            local_completed_time = self.convert_to_local_time(opportunity.completed_at)
                            completed_time = local_completed_time.strftime("%Y-%m-%d %H:%M")
                            time_text.append(f"Completed: {completed_time}")
                        time_info_parts = []
                        if total_time:
                            time_info_parts.append(f"Total Time: {self.format_duration(total_time)}")
                        if work_time:
                            time_info_parts.append(f"Work Time: {self.format_duration(work_time)}")
                            
                        time_text.append(f"✓ Completed by {acceptor.first_name} {acceptor.last_name}")
                        if time_info_parts:
                            time_text.append(" • ".join(time_info_parts))
                    elif opportunity.status.lower() == "in progress":
                        time_text.append(f"Assigned to: {acceptor.first_name} {acceptor.last_name}")
                        # Show both current total time and work time for in-progress tickets
                        current_time = datetime.now(timezone.utc)
                        total_duration = current_time - opportunity.created_at
                        time_text.append(f"Total Time: {self.format_duration(total_duration)}")
                        
                        if opportunity.started_at:
                            work_duration = current_time - opportunity.started_at
                            time_text.append(f"Work Time: {self.format_duration(work_duration)}")
                    else:
                        time_text.append(f"Assigned to: {acceptor.first_name} {acceptor.last_name}")
                
                time_info.setText(" • ".join(time_text))
                time_info.setStyleSheet("color: #888888; font-size: 11px;")
                title_section.addWidget(time_info)
                
                # Create details container
                details_container = QFrame()
                details_container.setStyleSheet("""
                    QFrame {
                        background-color: #2d2d2d;
                        border: 1px solid #3d3d3d;
                        border-radius: 4px;
                    }
                """)
                details_container_layout = QVBoxLayout(details_container)
                details_container_layout.setContentsMargins(12, 12, 12, 12)
                details_container_layout.setSpacing(8)
                details_container.hide()  # Hide the container initially
                
                # Add "More Details" button for compact mode
                details_btn = QPushButton("More Details ▼")
                details_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #0078d4;
                        border: none;
                        padding: 4px;
                        font-size: 12px;
                        text-align: left;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        color: #2196F3;
                    }
                """)
                
                # Create details content widget (hidden initially)
                details_content = QWidget()
                details_layout = QVBoxLayout(details_content)
                details_layout.setContentsMargins(0, 8, 0, 0)
                details_layout.setSpacing(8)
                
                # Add systems info
                if opportunity.systems or opportunity.systems_rel:
                    systems_frame = QFrame()
                    systems_frame.setStyleSheet("""
                        QFrame {
                            background-color: #262626;
                            border-radius: 4px;
                            padding: 8px;
                        }
                    """)
                    systems_layout = QVBoxLayout(systems_frame)
                    systems_layout.setSpacing(6)
                    
                    # Handle both JSONB systems and relationship systems
                    if opportunity.systems and isinstance(opportunity.systems, list):
                        for system_data in opportunity.systems:
                            system_text = f"• {system_data['system']}"
                            if system_data.get('affected_portions'):
                                system_text += f": {', '.join(system_data['affected_portions'])}"
                            system_label = QLabel(system_text)
                            system_label.setStyleSheet("color: #cccccc; font-size: 12px;")
                            system_label.setWordWrap(True)
                            systems_layout.addWidget(system_label)
                    
                    if opportunity.systems_rel:
                        for system in opportunity.systems_rel:
                            system_label = QLabel(f"• {system.name}")
                            system_label.setStyleSheet("color: #cccccc; font-size: 12px;")
                            system_label.setWordWrap(True)
                            systems_layout.addWidget(system_label)
                    
                    details_layout.addWidget(systems_frame)
                
                # Add description
                if opportunity.description:
                    desc_frame = QFrame()
                    desc_frame.setStyleSheet("""
                        QFrame {
                            background-color: #262626;
                            border-radius: 4px;
                            padding: 8px;
                        }
                    """)
                    desc_layout = QVBoxLayout(desc_frame)
                    
                    desc = QLabel(opportunity.description)
                    desc.setWordWrap(True)
                    desc.setStyleSheet("color: #cccccc; font-size: 12px; line-height: 1.4;")
                    desc_layout.addWidget(desc)
                    
                    details_layout.addWidget(desc_frame)
                
                # Add files
                if opportunity.files:
                    files_frame = QFrame()
                    files_frame.setStyleSheet("""
                        QFrame {
                            background-color: #262626;
                            border-radius: 4px;
                            padding: 8px;
                        }
                    """)
                    files_layout = QHBoxLayout(files_frame)
                    files_layout.setSpacing(8)
                    
                    for file in opportunity.files:
                        if not file.is_deleted:
                            file_btn = QPushButton(f"📎 {file.display_name}")
                            file_btn.setStyleSheet("""
                                QPushButton {
                                    background-color: #2d2d2d;
                                    color: #0078d4;
                                    border: none;
                                    border-radius: 4px;
                                    padding: 4px 8px;
                                    font-size: 12px;
                                    text-align: left;
                                }
                                QPushButton:hover {
                                    background-color: #333333;
                                    color: #2196F3;
                                }
                            """)
                            file_btn.clicked.connect(lambda checked, f=file: self.open_file(f))
                            files_layout.addWidget(file_btn)
                    
                    files_layout.addStretch()
                    details_layout.addWidget(files_frame)
                
                # Add comments section
                if opportunity.comments:
                    comments_btn = QPushButton(f"View Comments ({len(opportunity.comments)})")
                else:
                    comments_btn = QPushButton("Add Comment")
                comments_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #262626;
                        color: #0078d4;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 13px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #333333;
                        color: #2196F3;
                    }
                """)
                comments_btn.clicked.connect(lambda checked, o=opportunity: self.show_comments_dialog(o))
                details_layout.addWidget(comments_btn)
                
                details_container_layout.addWidget(details_content)
                
                # Toggle details visibility
                details_visible = False
                def toggle_details():
                    nonlocal details_visible
                    details_visible = not details_visible
                    details_container.setVisible(details_visible)  # Show/hide the container
                    details_btn.setText("Less Details ▲" if details_visible else "More Details ▼")
                
                details_btn.clicked.connect(toggle_details)
                title_section.addWidget(details_btn)
                title_section.addWidget(details_container)

            else:
                # Expanded mode: separate lines for better readability
                info_row = QHBoxLayout()
                info_row.setSpacing(16)
                
                # First row: Ticket ID and creator info
                ticket = QLabel(opportunity.title)
                ticket.setStyleSheet("color: #999999; font-size: 13px;")
                info_row.addWidget(ticket)
                
                submitter = QLabel(f"by {opportunity.creator.first_name} {opportunity.creator.last_name}")
                submitter.setStyleSheet("color: #999999; font-size: 13px;")
                info_row.addWidget(submitter)
                
                if opportunity.creator.team:
                    team = QLabel(f"({opportunity.creator.team})")
                    team.setStyleSheet("color: #666666; font-size: 13px;")
                    info_row.addWidget(team)
                
                info_row.addStretch()
                title_section.addLayout(info_row)
                
                # Second row: Timestamps and acceptor info
                time_row = QHBoxLayout()
                time_row.setSpacing(16)
                
                # Created timestamp
                if opportunity.created_at:
                    # Convert to local time for display
                    local_created_time = self.convert_to_local_time(opportunity.created_at)
                    created_time = local_created_time.strftime("%Y-%m-%d %H:%M")
                    created_label = QLabel(f"Created: {created_time}")
                    created_label.setStyleSheet("color: #888888; font-size: 12px;")
                    time_row.addWidget(created_label)
                
                # Acceptor info
                if opportunity.acceptor_id:
                    acceptor = opportunity.acceptor
                    if opportunity.status.lower() == "completed" and opportunity.completed_at:
                        duration = opportunity.completed_at - opportunity.created_at
                        time_info = QLabel(f"✓ Completed by {acceptor.first_name} {acceptor.last_name} in {self.format_duration(duration)}")
                        time_info.setStyleSheet("color: #00b300; font-size: 12px; font-weight: bold;")  # Green color for completion
                    else:
                        acceptor_label = QLabel(f"Assigned to: {acceptor.first_name} {acceptor.last_name}")
                        acceptor_label.setStyleSheet("color: #888888; font-size: 12px;")
                        time_info = QLabel(f"⏱ Active for {self.format_duration(datetime.now(timezone.utc) - opportunity.created_at)}")
                        time_info.setStyleSheet("color: #888888; font-size: 12px;")
                    
                    time_row.addWidget(time_info)
                
                time_row.addStretch()
                title_section.addLayout(time_row)
            
            header.addLayout(title_section)
            
            # Status section
            status_section = QHBoxLayout()
            status_section.setSpacing(8)
            
            status_combo = QComboBox()
            status_combo.addItems(["New", "In Progress", "Completed", "Needs Info"])
            status_combo.setCurrentText(opportunity.status.title())
            status_combo.setStyleSheet(f"""
                QComboBox {{
                    background-color: #262626;
                    color: white;
                    border: 1px solid #404040;
                    padding: {4 if self.is_compact else 6}px {8 if self.is_compact else 12}px;
                    border-radius: 4px;
                    min-width: {100 if self.is_compact else 140}px;
                }}
                QComboBox::drop-down {{
                    border: none;
                    padding-right: 8px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 4px solid white;
                }}
            """)
            status_combo.setProperty("opportunity", opportunity)
            status_combo.currentTextChanged.connect(self.handle_status_change)
            status_section.addWidget(status_combo)
            
            if not self.is_compact and opportunity.acceptor_id:
                time_info = QLabel()
                if opportunity.status.lower() == "completed" and opportunity.completed_at and opportunity.created_at:
                    duration = opportunity.completed_at - opportunity.created_at
                    time_info.setText(f"✓ Completed by {opportunity.acceptor.first_name} {opportunity.acceptor.last_name} in {self.format_duration(duration)}")
                elif opportunity.status.lower() == "in progress" and opportunity.created_at:
                    duration = datetime.now(timezone.utc) - opportunity.created_at
                    time_info.setText(f"⏱ Active for {self.format_duration(duration)}")
                time_info.setStyleSheet("color: #999999; font-size: 13px;")
                status_section.addWidget(time_info)
            
            header.addLayout(status_section)
            card_layout.addLayout(header)
            
            # Content section - only show in expanded mode
            if not self.is_compact:
                content = QVBoxLayout()
                content.setSpacing(16)
                content.setContentsMargins(0, 8, 0, 0)
                
                # Systems section
                if opportunity.systems:
                    systems_layout = QVBoxLayout()
                    systems_layout.setSpacing(12)
                    
                    for system_data in opportunity.systems:
                        system_widget = QWidget()
                        system_layout = QVBoxLayout(system_widget)
                        system_layout.setSpacing(4)
                        system_layout.setContentsMargins(0, 0, 0, 0)
                        
                        system_header = QHBoxLayout()
                        system_name = QLabel(f"• {system_data['system']}")
                        system_name.setStyleSheet("color: #0078d4; font-weight: bold; font-size: 14px;")
                        system_header.addWidget(system_name)
                        system_header.addStretch()
                        system_layout.addLayout(system_header)
                        
                        if system_data.get('affected_portions'):
                            portions = QLabel(" · ".join(system_data['affected_portions']))
                            portions.setStyleSheet("color: #cccccc; font-size: 13px; padding-left: 16px;")
                            system_layout.addWidget(portions)
                        
                        systems_layout.addWidget(system_widget)
                    
                    content.addLayout(systems_layout)
                
                # Description
                if opportunity.description:
                    desc = QLabel(opportunity.description)
                    desc.setWordWrap(True)
                    desc.setStyleSheet("color: #cccccc; font-size: 13px; line-height: 1.4;")
                    content.addWidget(desc)
                
                # Files
                if opportunity.files:
                    files_layout = QHBoxLayout()
                    files_layout.setSpacing(8)
                    
                    for file in opportunity.files:
                        if not file.is_deleted:
                            file_btn = QPushButton(f"📎 {file.display_name}")
                            file_btn.setStyleSheet("""
                                QPushButton {
                                    background-color: #262626;
                                    color: #0078d4;
                                    border: none;
                                    border-radius: 4px;
                                    padding: 6px 12px;
                                    font-size: 13px;
                                    text-align: left;
                                }
                                QPushButton:hover {
                                    background-color: #333333;
                                    color: #2196F3;
                                }
                            """)
                            file_btn.clicked.connect(lambda checked, f=file: self.open_file(f))
                            files_layout.addWidget(file_btn)
                    
                    files_layout.addStretch()
                    content.addLayout(files_layout)
                
                card_layout.addLayout(content)
            
            card.setLayout(card_layout)
            self.opportunities_layout.addWidget(card)
            return card
            
        except Exception as e:
            print(f"Error creating opportunity widget: {str(e)}")
            traceback.print_exc()
            return None

    def format_file_size(self, size_in_bytes):
        """Format file size in a human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024.0:
                return f"{size_in_bytes:.1f} {unit}"
            size_in_bytes /= 1024.0
        return f"{size_in_bytes:.1f} TB"

    def open_file(self, file):
        """Open the file using the system's default application"""
        try:
            from app.services.supabase_storage import SupabaseStorageService
            
            if SupabaseStorageService.file_exists(file.storage_path):
                if SupabaseStorageService.open_file(file.storage_path):
                    print(f"Successfully opened file: {file.original_name}")
                else:
                    QMessageBox.warning(self, "Error Opening File", "Could not open the file with the default application.")
            else:
                QMessageBox.warning(self, "File Not Found", "The file could not be found in the storage location.")
        except Exception as e:
            QMessageBox.warning(self, "Error Opening File", f"An error occurred while trying to open the file: {e}")

    def handle_status_change(self, new_status):
        """Handle status change from combo box"""
        try:
            print(f"\nDEBUG: Status change initiated - New status: {new_status}")
            combo = self.sender()  # Get the combo box that sent the signal
            if not combo:
                print("DEBUG: No combo box found as sender")
                return
            
            # Get the opportunity from the combo box property
            opportunity = combo.property("opportunity")
            if not opportunity:
                print("DEBUG: No opportunity found in combo box property")
                return
            
            print(f"DEBUG: Found opportunity {opportunity.id} for status change")
            
            # Show dialog for "Needs Info" or "Completed" status
            if new_status in ["Needs Info", "Completed"]:
                dialog = StatusChangeDialog(opportunity, new_status, self)
                if dialog.exec_() == QDialog.Accepted:
                    comment = dialog.get_comment()
                    if new_status == "Needs Info" and not comment:
                        QMessageBox.warning(self, "Required Information", "Please specify what information is needed.")
                        combo.setCurrentText(opportunity.status.title())  # Revert the combo box
                        return
                    # Update the status with the comment
                    self.update_status(opportunity, new_status, comment)
                else:
                    # Dialog was cancelled, revert the combo box
                    combo.setCurrentText(opportunity.status.title())
            else:
                # For other statuses, update directly
                self.update_status(opportunity, new_status)
            
        except Exception as e:
            print(f"ERROR in handle_status_change: {str(e)}")
            print("Traceback:", traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while handling status change: {str(e)}")

    def update_status(self, opportunity: Opportunity, new_status: str, comment: Optional[str] = None) -> None:
        """Update the status of an opportunity"""
        try:
            utc = ZoneInfo('UTC')
            now = datetime.now().replace(tzinfo=utc)
            
            # Debug prints
            print(f"Updating status for opportunity {opportunity.id}")
            print(f"New status: {new_status}")
            print(f"Current user: {self.current_user.id if self.current_user else None}")
            
            db = SessionLocal()
            try:
                # Get fresh opportunity from database
                opportunity = cast(Opportunity, db.query(Opportunity).filter(Opportunity.id == opportunity.id).first())
                if not opportunity:
                    return
                
                # Add comment if provided
                if comment:
                    comment_data = {
                        "user_id": str(self.current_user.id) if self.current_user else None,
                        "text": comment,
                        "user_name": f"{self.current_user.first_name} {self.current_user.last_name}" if self.current_user else "Unknown"
                    }
                    if not getattr(opportunity, 'comments', None):
                        setattr(opportunity, 'comments', [])
                    getattr(opportunity, 'comments').append(comment_data)
                
                # Debug prints
                print(f"Old status: {str(opportunity.status)}")
                print(f"Updating to: {new_status}")
                
                # Update status and related fields
                if new_status.lower() == "in progress":
                    if not opportunity.acceptor_id and self.current_user:
                        setattr(opportunity, 'acceptor_id', self.current_user.id)
                    if not opportunity.started_at:
                        setattr(opportunity, 'started_at', now)
                    
                    activity_details = {
                        "action": "status_change",
                        "old_status": str(opportunity.status),
                        "new_status": new_status,
                        "acceptor": f"{self.current_user.first_name} {self.current_user.last_name}" if self.current_user else None
                    }
                    
                elif new_status.lower() == "completed":
                    setattr(opportunity, 'completed_at', now)
                    if opportunity.started_at:
                        setattr(opportunity, 'response_time', sql_cast(now - opportunity.created_at, Interval))
                        setattr(opportunity, 'work_time', sql_cast(now - opportunity.started_at, Interval))
                    
                    activity_details = {
                        "action": "status_change",
                        "old_status": str(opportunity.status),
                        "new_status": new_status,
                        "completed_by": f"{self.current_user.first_name} {self.current_user.last_name}" if self.current_user else None
                    }
                    
                elif new_status.lower() == "needs info":
                    activity_details = {
                        "action": "needs_info",
                        "old_status": str(opportunity.status),
                        "new_status": new_status,
                        "requested_by": f"{self.current_user.first_name} {self.current_user.last_name}" if self.current_user else None,
                        "info_needed": comment
                    }
                    
                else:
                    activity_details = {
                        "action": "status_change",
                        "old_status": str(opportunity.status),
                        "new_status": new_status
                    }
                
                # Create activity log entry
                activity_log = ActivityLog(
                    opportunity_id=str(opportunity.id),
                    user_id=str(self.current_user.id) if self.current_user else None,
                    action="status_change",
                    details=activity_details
                )
                db.add(activity_log)
                
                # Update opportunity status and timestamp
                setattr(opportunity, 'status', new_status)
                setattr(opportunity, 'updated_at', now)
                
                db.commit()
                
                # Emit signal to refresh other components
                self.refresh_needed.emit()
                
                # Refresh the dashboard
                self.load_opportunities()
                
            except Exception as e:
                print(f"ERROR in update_status: {str(e)}")
                print("Traceback:", traceback.format_exc())
                db.rollback()
                QMessageBox.critical(self, "Error", f"An error occurred while updating the ticket status: {str(e)}")
            finally:
                db.close()
        except Exception as e:
            print(f"ERROR in update_status: {str(e)}")
            print("Traceback:", traceback.format_exc())

    def format_duration(self, duration: Optional[timedelta]) -> str:
        """Format a timedelta into a readable string with error handling"""
        try:
            if duration is None:
                return "N/A"
            
            if isinstance(duration, ColumnElement):
                # If it's a SQLAlchemy column, we need to get its Python value
                duration = cast(timedelta, duration)
            
            total_seconds = int(duration.total_seconds())
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            parts: List[str] = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0 or days > 0:  # Show hours if there are days
                parts.append(f"{hours:02d}h")
            if minutes > 0 or hours > 0 or days > 0:  # Show minutes if there are hours or days
                parts.append(f"{minutes:02d}m")
            if not parts or seconds > 0:  # Always show seconds if no larger units or if there are seconds
                parts.append(f"{seconds:02d}s")
            
            return " ".join(cast(Iterable[str], parts))
            
        except Exception as e:
            print(f"Error formatting duration: {str(e)}")
            return "N/A"

    def create_filter_buttons(self):
        """Create filter buttons"""
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        filters = [
            ("All", "all"),
            ("My Tickets", "my_tickets"),
            ("New", "new"),
            ("In Progress", "in_progress"),
            ("Needs Info", "needs_info"),
            ("Completed", "completed")
        ]
        
        button_style = """
            QPushButton {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
                border: 1px solid #666666;
            }
            QPushButton:checked {
                background-color: #0078d4;
                border: 1px solid #0078d4;
            }
        """
        
        for label, filter_id in filters:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(filter_id == "all")  # Set "All" as default
            btn.setProperty("filter_id", filter_id)
            btn.setStyleSheet(button_style)
            btn.clicked.connect(lambda checked, fid=filter_id: self.apply_filter(fid))
            filter_layout.addWidget(btn)
        
        filter_layout.addStretch()
        return filter_layout

    def toggle_view_mode(self):
        """Toggle between compact and expanded view modes"""
        self.is_compact = not self.is_compact
        self.view_toggle_btn.setText("Compact View" if self.is_compact else "Expanded View")
        
        # Update window size
        if self.is_compact:
            screen = QApplication.primaryScreen().availableGeometry()
            self.resize(int(screen.width() * 0.5), int(screen.height() * 0.6))  # Slightly smaller size
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            self.resize(int(screen.width() * 0.8), int(screen.height() * 0.8))
        
        # Refresh the opportunities to update their layout
        self.load_opportunities() 

    def focus_ticket(self, ticket_id):
        """Focus on a specific ticket by ID"""
        if not ticket_id:
            return
            
        # Ensure the ticket is loaded
        self.current_filter = "all"  # Switch to all tickets view
        self.load_opportunities()
        
        # Find and scroll to the ticket widget
        if ticket_id in self.opportunity_widgets:
            widget = self.opportunity_widgets[ticket_id]
            # Ensure the widget is visible
            scroll_area = self.findChild(QScrollArea)
            if scroll_area:
                # Calculate position to scroll to
                widget_pos = widget.mapTo(scroll_area.widget(), QPoint(0, 0))
                scroll_area.ensureVisible(0, widget_pos.y(), 0, widget.height() // 2)
                
                # Highlight the ticket briefly
                original_style = widget.styleSheet()
                highlight_style = """
                    QFrame {
                        background-color: #0078d4;
                        border-radius: 6px;
                        padding: 12px;
                    }
                """
                widget.setStyleSheet(highlight_style)
                
                # Reset style after a delay
                QTimer.singleShot(1000, lambda: widget.setStyleSheet(original_style)) 

    def show_comments_dialog(self, opportunity):
        """Show dialog for viewing and adding comments"""
        try:
            # Get fresh opportunity data from database
            db = SessionLocal()
            fresh_opp = db.query(Opportunity).filter(Opportunity.id == opportunity.id).first()
            if fresh_opp:
                # Update the opportunity object with fresh data
                opportunity.comments = fresh_opp.comments
            db.close()
            
            dialog = CommentDialog(opportunity, self)
            if dialog.exec_() == QDialog.Accepted:
                comment = dialog.get_comment()
                if comment:
                    print(f"Adding comment: {comment}")  # Debug print
                    # Add the comment and update the dashboard
                    self.add_comment(opportunity, comment)

        except Exception as e:
            print(f"Error showing comments dialog: {str(e)}")
            print("Traceback:", traceback.format_exc())
            QMessageBox.critical(self, "Error", f"An error occurred while showing comments: {str(e)}")

    def add_comment(self, opportunity, comment):
        """Add a comment to an opportunity"""
        try:
            now = datetime.now(timezone.utc)
            db = SessionLocal()
            
            # Get fresh opportunity data
            opp = db.query(Opportunity).filter(Opportunity.id == opportunity.id).first()
            if not opp:
                print("ERROR: Opportunity not found")
                return None
            
            # Initialize comments list if it doesn't exist
            if opp.comments is None:
                opp.comments = []
            
            # Add the new comment with consistent structure
            comment_data = {
                'user_id': str(self.current_user.id),
                'user_name': f"{self.current_user.first_name} {self.current_user.last_name}",
                'text': comment,
                'timestamp': now.isoformat()  # Store as ISO format string
            }
            
            # Debug print
            print(f"Adding comment: {comment_data}")
            print(f"Current comments: {opp.comments}")
            
            # Append the new comment to the JSONB array
            opp.comments = opp.comments + [comment_data]
                
            print(f"Updated comments: {opp.comments}")
            
            # Create notification for the other party
            target_user_id = opp.creator_id if self.current_user.id != opp.creator_id else opp.acceptor_id
            if target_user_id:
                notification = Notification(
                    user_id=target_user_id,
                    opportunity_id=opp.id,
                    type="comment",
                    message=f"New comment on ticket '{opp.title}' from {self.current_user.first_name} {self.current_user.last_name}",
                    created_at=now,
                    read=False
                )
                db.add(notification)
            
            # Commit the changes
            db.commit()
            print(f"Comment saved successfully. Total comments: {len(opp.comments)}")
            
            # Update the original opportunity object with new comments
            opportunity.comments = opp.comments
            
            # Force a refresh of the dashboard to update comment counts
            self.load_opportunities()
            
            # Show success message
            QMessageBox.information(self, "Success", "Comment added successfully!")
            
        except Exception as e:
            print(f"ERROR adding comment: {str(e)}")
            print("Traceback:", traceback.format_exc())
            db.rollback()
            QMessageBox.critical(self, "Error", f"An error occurred while adding the comment: {str(e)}")
        finally:
            db.close()

    def show_refresh_animation(self):
        """Show the refresh animation in the center of the view"""
        if not hasattr(self, 'refresh_animation') or not hasattr(self, 'refresh_message'):
            return
            
        # Position in center of visible area
        viewport_rect = self.scroll_area.viewport().rect()
        global_pos = self.scroll_area.viewport().mapToGlobal(viewport_rect.center())
        local_pos = self.mapFromGlobal(global_pos)
        
        # Position the spinner
        self.refresh_animation.move(local_pos.x() - 20, local_pos.y() - 20)
        self.refresh_animation.raise_()  # Make sure it's on top
        self.refresh_animation.show()
        
        # Start spinner animation
        self.spinner_angle = 0
        self.spinner_timer.start(50)  # Update every 50ms
        
        # Update immediately to show first frame
        self.update_spinner()
        print("DEBUG: Showing refresh animation")

    def hide_refresh_animation(self):
        """Hide refresh animation and show confirmation"""
        if not hasattr(self, 'refresh_animation') or not hasattr(self, 'refresh_message'):
            return
            
        # Stop and hide spinner
        self.spinner_timer.stop()
        self.refresh_animation.hide()
        
        # Show "Refreshed!" message where the spinner was
        self.refresh_message.setText("Refreshed!")
        self.refresh_message.adjustSize()
        
        pos = self.refresh_animation.pos()
        self.refresh_message.move(
            pos.x() - (self.refresh_message.width() - self.refresh_animation.width()) // 2,
            pos.y() - (self.refresh_message.height() - self.refresh_animation.height()) // 2
        )
        
        # Show with full opacity
        self.fade_opacity = 1.0
        self.refresh_message.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-size: 14px;
                font-weight: bold;
                background-color: rgba(30, 30, 30, 220);
                border-radius: 4px;
                padding: 6px 10px;
            }
        """)
        self.refresh_message.raise_()  # Make sure it's on top
        self.refresh_message.show()
        
        # Start fade timer
        self.fade_timer.start(50)  # Fade over time
        print("DEBUG: Showing refresh completion message")
        
    def update_spinner(self):
        """Update the spinner animation frame"""
        if not self.refresh_animation or not self.refresh_animation.isVisible():
            return
            
        self.spinner_angle = (self.spinner_angle + 10) % 360
        
        # Draw the spinner
        pixmap = QPixmap(40, 40)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set color for the spinner
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#0078d4"))
        
        # Draw the spinning arc
        rect = QRect(5, 5, 30, 30)
        painter.drawPie(rect, self.spinner_angle * 16, 120 * 16)  # 120 degrees arc
        
        # Add a white dot at the end of the arc for better visibility
        end_angle = (self.spinner_angle + 120) % 360
        end_x = 20 + 15 * math.cos(math.radians(end_angle))
        end_y = 20 + 15 * math.sin(math.radians(end_angle))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QPoint(int(end_x), int(end_y)), 3, 3)
        
        painter.end()
        
        self.refresh_animation.setPixmap(pixmap)
        
    def fade_message(self):
        """Fade out the refresh confirmation message"""
        if not self.refresh_message or not self.refresh_message.isVisible():
            self.fade_timer.stop()
            return
            
        self.fade_opacity -= 0.05
        if self.fade_opacity <= 0:
            self.refresh_message.hide()
            self.fade_timer.stop()
            return
            
        # Update opacity using stylesheet
        self.refresh_message.setStyleSheet(f"""
            QLabel {{
                color: #0078d4;
                font-size: 14px;
                font-weight: bold;
                background-color: rgba(255, 255, 255, {int(220 * self.fade_opacity)});
                border-radius: 4px;
                padding: 6px 10px;
            }}
        """)
        
class StatusChangeDialog(QDialog):
    def __init__(self, opportunity, new_status, parent=None):
        super().__init__(parent)
        self.opportunity = opportunity
        self.new_status = new_status
        self.comment = None
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Title
        title = QLabel(f"Update Status to {self.new_status}")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
        """)
        layout.addWidget(title)
        
        # Comment field
        comment_label = QLabel("Additional Information:" if self.new_status == "Completed" else "Information Needed:")
        comment_label.setStyleSheet("color: white;")
        layout.addWidget(comment_label)
        
        self.comment_edit = QTextEdit()
        self.comment_edit.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.comment_edit.setPlaceholderText(
            "Add completion notes (optional)..." if self.new_status == "Completed"
            else "Specify what information is needed..."
        )
        layout.addWidget(self.comment_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        update_btn = QPushButton("Update Status")
        update_btn.setStyleSheet("""
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
        update_btn.clicked.connect(self.accept)
        button_layout.addWidget(update_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: #1e1e1e;")
        self.setWindowTitle("Status Update")
        self.setMinimumWidth(400)
        
    def accept(self):
        """Override accept to validate and store comment before closing"""
        self.comment = self.comment_edit.toPlainText().strip()
        if not self.comment:
            QMessageBox.warning(self, "Empty Response", "Please enter a response before submitting.")
            return
        super().accept()
        
    def get_comment(self):
        """Return the stored comment"""
        return self.comment

class CommentDialog(QDialog):
    def __init__(self, opportunity, parent=None):
        super().__init__(parent)
        self.opportunity = opportunity
        self.comment = None
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(16)
        
        # Title
        title = QLabel("Add Response")
        title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: white;
        """)
        layout.addWidget(title)
        
        # Previous comments
        if self.opportunity.comments:
            comments_frame = QFrame()
            comments_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    padding: 8px;
                }
            """)
            comments_layout = QVBoxLayout(comments_frame)
            
            for comment in self.opportunity.comments:
                comment_widget = QFrame()
                comment_widget.setStyleSheet("""
                    QFrame {
                        background-color: #262626;
                        border-radius: 4px;
                        padding: 8px;
                        margin-bottom: 4px;
                    }
                """)
                comment_layout = QVBoxLayout(comment_widget)
                
                # Format timestamp if it exists
                timestamp = comment.get('timestamp', '')
                if timestamp:
                    try:
                        # Parse ISO format timestamp
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        formatted_time = timestamp
                else:
                    formatted_time = "Unknown time"
                
                header = QLabel(f"{comment.get('user_name', 'Unknown User')} • {formatted_time}")
                header.setStyleSheet("color: #888888; font-size: 11px;")
                comment_layout.addWidget(header)
                
                text = QLabel(comment.get('text', ''))
                text.setWordWrap(True)
                text.setStyleSheet("color: white; font-size: 12px;")
                comment_layout.addWidget(text)
                
                if comment.get('type'):
                    type_label = QLabel(f"Status changed to: {comment['type']}")
                    type_label.setStyleSheet("color: #0078d4; font-size: 11px;")
                    comment_layout.addWidget(type_label)
                
                comments_layout.addWidget(comment_widget)
            
            layout.addWidget(comments_frame)
        
        # Comment field
        comment_label = QLabel("Your Response:")
        comment_label.setStyleSheet("color: white;")
        layout.addWidget(comment_label)
        
        self.comment_edit = QTextEdit()
        self.comment_edit.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.comment_edit.setPlaceholderText("Type your response here...")
        layout.addWidget(self.comment_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3d3d3d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        submit_btn = QPushButton("Submit Response")
        submit_btn.setStyleSheet("""
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
        submit_btn.clicked.connect(self.accept)
        button_layout.addWidget(submit_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("background-color: #1e1e1e;")
        self.setWindowTitle("Add Response")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
    def accept(self):
        """Override accept to validate and store comment before closing"""
        self.comment = self.comment_edit.toPlainText().strip()
        if not self.comment:
            QMessageBox.warning(self, "Empty Response", "Please enter a response before submitting.")
            return
        super().accept()
        
    def get_comment(self):
        """Return the stored comment"""
        return self.comment 