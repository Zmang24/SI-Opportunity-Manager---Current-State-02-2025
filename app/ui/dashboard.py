from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QScrollArea, QFrame, QMessageBox, QComboBox, QDateEdit,
                           QDialog, QTextEdit, QSlider, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QDate, QPoint, QRect, QObject, QEvent, QSize
from PyQt5.QtGui import QCloseEvent, QKeySequence, QPainter, QPixmap, QColor, QFont
from app.database.connection import SessionLocal
from app.models.models import Opportunity, Notification, ActivityLog, User, Vehicle, File
from sqlalchemy.orm import joinedload
from app.services.supabase_storage import SupabaseStorageService
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
import re

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
        self.current_filter: str = "new"  # Changed back to "new" as the default filter
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
                except Exception as e:
                    print(f"DEBUG: Error creating ZoneInfo: {str(e)}")
                    return ZoneInfo('UTC')
            else:
                print("DEBUG: No valid timezone found")
                return ZoneInfo('UTC')
        except Exception as e:
            print(f"DEBUG: Error getting local timezone: {str(e)}")
            return ZoneInfo('UTC')

    def get_filtered_opportunities(self, db: Session) -> List[Opportunity]:
        """Get opportunities based on current filter"""
        print(f"DEBUG: Applying filter: {self.current_filter}")
        print(f"DEBUG: Advanced filter applied: {self.advanced_filter_applied}")
        
        # Base query with files relationship loaded
        query = db.query(Opportunity).options(joinedload(Opportunity.files))
        
        # Apply filter based on filter button
        if self.current_filter == "active_tickets":
            # Show all tickets except completed ones
            query = query.filter(~Opportunity.status.ilike("completed"))
            print(f"DEBUG: Applied 'Active Tickets' filter (excluding completed)")
        elif self.current_filter == "my_tickets":
            # My tickets filter (created by me)
            query = query.filter(Opportunity.creator_id == str(self.current_user.id))
            print(f"DEBUG: Applied 'My Tickets' filter")
            
            # Sub-filter for my tickets
            if self.my_tickets_filter_type.currentText() == "Created":
                # Already filtered to my created tickets
                pass
            elif self.my_tickets_filter_type.currentText() == "Assigned":
                # Switch to assigned tickets
                query = db.query(Opportunity).filter(Opportunity.acceptor_id == str(self.current_user.id))
                print(f"DEBUG: Applied 'Assigned to Me' sub-filter")
            elif self.my_tickets_filter_type.currentText() == "Both":
                # Both created by me and assigned to me
                query = db.query(Opportunity).filter(
                    (Opportunity.creator_id == str(self.current_user.id)) | 
                    (Opportunity.acceptor_id == str(self.current_user.id))
                )
                print(f"DEBUG: Applied 'Both' sub-filter")
        elif self.current_filter == "new":
            query = query.filter(Opportunity.status.ilike("new"))
            # Only show tickets that aren't created by current user
            if self.current_user:
                query = query.filter(Opportunity.creator_id != str(self.current_user.id))
            print(f"DEBUG: Applied 'New' filter")
        elif self.current_filter == "in_progress":
            query = query.filter(Opportunity.status.ilike("in progress"))
            print(f"DEBUG: Applied 'In Progress' filter")
        elif self.current_filter == "completed":
            query = query.filter(Opportunity.status.ilike("completed"))
            print(f"DEBUG: Applied 'Completed' filter")
        elif self.current_filter == "needs_info":
            query = query.filter(Opportunity.status.ilike("needs info"))
            print(f"DEBUG: Applied 'Needs Info' filter")
        
        # Apply advanced filters if set
        if self.advanced_filter_applied:
            # Status filter
            if self.status_filter.currentText() != "All":
                query = query.filter(Opportunity.status.ilike(self.status_filter.currentText().lower()))
                print(f"DEBUG: Applied advanced status filter: {self.status_filter.currentText()}")
            
            # Assignment filter
            if self.assignment_filter.currentText() == "Assigned To Me":
                query = query.filter(Opportunity.acceptor_id == str(self.current_user.id))
                print(f"DEBUG: Applied 'Assigned To Me' filter")
            elif self.assignment_filter.currentText() == "Created By Me":
                query = query.filter(Opportunity.creator_id == str(self.current_user.id))
                print(f"DEBUG: Applied 'Created By Me' filter")
            elif self.assignment_filter.currentText() == "Unassigned":
                query = query.filter(Opportunity.acceptor_id == None)
                print(f"DEBUG: Applied 'Unassigned' filter")
            
            # Date range
            start_date = self.from_date.date().toPyDate()
            end_date = self.to_date.date().toPyDate()
            
            # Add a day to the end date to make it inclusive
            end_date = end_date + timedelta(days=1)
            
            # Get timezone info
            utc = ZoneInfo('UTC')
            
            if start_date and end_date:
                query = query.filter(
                    Opportunity.created_at.between(
                        datetime.combine(start_date, datetime.min.time(), tzinfo=utc),
                        datetime.combine(end_date, datetime.max.time(), tzinfo=utc)
                    ))
                print(f"DEBUG: Applied date filter: {start_date} to {end_date}")
            else:
                print(f"DEBUG: No date range filter applied")
        
        # Get vehicle information if available by joining with Vehicle table
        try:
            # Check if the vehicles table exists and has matching records
            vehicles_exists = db.query(Vehicle).limit(1).count() > 0
            if vehicles_exists:
                # Look for vehicle_id if it exists as a direct column
                if hasattr(Opportunity, 'vehicle_id'):
                    query = query.outerjoin(Vehicle, Vehicle.id == Opportunity.vehicle_id)
                    print(f"DEBUG: Joined with vehicles table using vehicle_id")
                # Otherwise try to join using VIN if both tables have it
                elif hasattr(Opportunity, 'vin') and hasattr(Vehicle, 'vin'):
                    query = query.outerjoin(Vehicle, Vehicle.vin == Opportunity.vin)
                    print(f"DEBUG: Joined with vehicles table using VIN")
        except Exception as e:
            print(f"DEBUG: Error trying to join with vehicles: {str(e)}")
            # Continue without the join if there's an error
        
        # Return results ordered by creation date
        return query.order_by(Opportunity.created_at.desc()).all()

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
            
            # Display vehicle info as the main title instead of ticket number
            vehicle_info_display = []
            has_vehicle_for_title = False
            
            # Check if this is a referenced vehicle through a join
            if hasattr(opportunity, 'vehicle') and opportunity.vehicle:
                vehicle = opportunity.vehicle
                if vehicle and hasattr(vehicle, 'year') and hasattr(vehicle, 'make') and hasattr(vehicle, 'model'):
                    vehicle_info_display = [vehicle.year, vehicle.make, vehicle.model]
                    has_vehicle_for_title = True
            # Otherwise check for year/make/model attributes directly on opportunity
            elif hasattr(opportunity, 'year') and opportunity.year and hasattr(opportunity, 'make') and opportunity.make and hasattr(opportunity, 'model') and opportunity.model:
                vehicle_info_display = [opportunity.year, opportunity.make, opportunity.model]
                has_vehicle_for_title = True
            # Otherwise try to extract from description
            elif opportunity.description:
                # Look for "Vehicle: YEAR MAKE MODEL" pattern in the description
                vehicle_match = re.search(r'Vehicle:\s+([^\n]+)', opportunity.description)
                if vehicle_match:
                    vehicle_str = vehicle_match.group(1).strip()
                    if vehicle_str:
                        vehicle_info_display = [vehicle_str]
                        has_vehicle_for_title = True
            
            # Use vehicle info as title if available, otherwise fall back to ticket number
            if has_vehicle_for_title and vehicle_info_display:
                title_text = " ".join(vehicle_info_display)
            else:
                title_text = f"{opportunity.display_title if hasattr(opportunity, 'display_title') else opportunity.title}"
            
            title = QLabel(title_text)
            title.setStyleSheet(f"""
                color: #ffffff;
                font-size: {14 if self.is_compact else 18}px;
                font-weight: bold;
            """)
            title_section.addWidget(title)
            
            # Add submitter info
            if opportunity.creator:
                creator = opportunity.creator
                submitter_text = QLabel(f"Submitted by {creator.first_name} {creator.last_name} ({creator.team})")
                submitter_text.setStyleSheet("color: #bbbbbb; font-size: 12px;")
                title_section.addWidget(submitter_text)
            
            # Add time info
            time_info = QLabel()
            time_text = []
            
            if opportunity.created_at:
                # Convert to local time for display
                local_created_time = self.convert_to_local_time(opportunity.created_at)
                created_time = local_created_time.strftime("%Y-%m-%d %H:%M")
                time_text.append(f"Created: {created_time}")
            
            # Add acceptor info if assigned
            if opportunity.acceptor_id:
                acceptor = opportunity.acceptor
                if acceptor:
                    # If completed, show completion info
                    if opportunity.status.lower() == "completed":
                        # Include response and work time if available
                        total_time = opportunity.response_time
                        work_time = opportunity.work_time
                        
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
            
            # Add vehicle, systems, and description information
            if opportunity.vin or hasattr(opportunity, 'systems') or opportunity.description:
                details_frame = QFrame()
                details_frame.setStyleSheet("""
                    QFrame {
                        background-color: #252525;
                        border-radius: 4px;
                        padding: 8px;
                        margin-top: 4px;
                    }
                """)
                details_layout = QVBoxLayout(details_frame)
                details_layout.setContentsMargins(8, 8, 8, 8)
                details_layout.setSpacing(6)
                
                # Ticket number (moved from title to details)
                ticket_label = QLabel(f"Ticket: {opportunity.display_title if hasattr(opportunity, 'display_title') else opportunity.title}")
                ticket_label.setStyleSheet("color: #0078d4; font-size: 12px; font-weight: bold;")
                ticket_label.setWordWrap(True)
                details_layout.addWidget(ticket_label)
                
                # Add VIN if available
                if opportunity.vin:
                    vin_label = QLabel(f"VIN: {opportunity.vin}")
                    vin_label.setStyleSheet("color: #0078d4; font-size: 12px;")
                    details_layout.addWidget(vin_label)
                
                # Systems info (if available)
                if hasattr(opportunity, 'systems') and opportunity.systems:
                    systems_str = ""
                    if isinstance(opportunity.systems, list):
                        systems = []
                        for system in opportunity.systems:
                            if isinstance(system, dict) and "system" in system:
                                systems.append(system["system"])
                            elif isinstance(system, dict) and "name" in system:
                                systems.append(system["name"])
                            elif isinstance(system, str):
                                systems.append(system)
                        systems_str = ", ".join(systems)
                    
                    if systems_str:
                        systems_label = QLabel(f"Systems: {systems_str}")
                        systems_label.setStyleSheet("color: #0078d4; font-size: 12px;")
                        systems_label.setWordWrap(True)
                        details_layout.addWidget(systems_label)
                
                # Attachments info (if available)
                if hasattr(opportunity, 'files') and opportunity.files:
                    files_container = QFrame()
                    files_container.setStyleSheet("""
                        QFrame {
                            background-color: transparent;
                            border-radius: 0px;
                            padding: 0px;
                        }
                    """)
                    files_layout = QVBoxLayout(files_container)
                    files_layout.setContentsMargins(0, 0, 0, 0)
                    files_layout.setSpacing(2)
                    
                    # Attachments header
                    attachments_header = QLabel(f"Attachments ({len(opportunity.files)}):")
                    attachments_header.setStyleSheet("color: #0078d4; font-size: 12px; font-weight: bold;")
                    files_layout.addWidget(attachments_header)
                    
                    # List attachments (show up to 3, then "and X more...")
                    displayed_files = 0
                    max_display = 3
                    
                    for file in opportunity.files:
                        if displayed_files < max_display:
                            file_link = QPushButton(f"📎 {file.display_name}")
                            file_link.setStyleSheet("""
                                QPushButton {
                                    background-color: transparent;
                                    color: #0078d4;
                                    border: none;
                                    text-align: left;
                                    padding: 2px 0px;
                                    font-size: 11px;
                                }
                                QPushButton:hover {
                                    color: #2196F3;
                                    text-decoration: underline;
                                }
                            """)
                            file_link.setCursor(Qt.PointingHandCursor)
                            file_link.clicked.connect(lambda checked, f=file: self.open_attachment(f))
                            files_layout.addWidget(file_link)
                            displayed_files += 1
                    
                    # If there are more files, show count
                    remaining_files = len(opportunity.files) - displayed_files
                    if remaining_files > 0:
                        more_label = QLabel(f"... and {remaining_files} more file(s)")
                        more_label.setStyleSheet("color: #888888; font-size: 11px; font-style: italic;")
                        files_layout.addWidget(more_label)
                    
                    details_layout.addWidget(files_container)
                
                # First comment or description (if available)
                description = ""
                if hasattr(opportunity, 'comments') and opportunity.comments and isinstance(opportunity.comments, list) and len(opportunity.comments) > 0:
                    # Get the first comment's text
                    if isinstance(opportunity.comments[0], dict) and 'text' in opportunity.comments[0]:
                        description = opportunity.comments[0]['text']
                elif opportunity.description:
                    description = opportunity.description
                    # Remove the Vehicle: line from displayed description since we now show vehicle in title
                    description = re.sub(r'Vehicle:\s+[^\n]+(\n|$)', '', description).strip()
                
                if description:
                    # Create a container for the description with a frame
                    desc_container = QFrame()
                    desc_container.setStyleSheet("""
                        QFrame {
                            background-color: transparent;
                            border-radius: 0px;
                            padding: 0px;
                        }
                        QFrame:hover {
                            background-color: #303030;
                        }
                    """)
                    desc_container_layout = QVBoxLayout(desc_container)
                    desc_container_layout.setContentsMargins(0, 0, 0, 0)
                    desc_container_layout.setSpacing(4)
                    
                    # Full description for storage
                    desc_container.full_description = description
                    
                    # Truncated description for initial display
                    max_length = 150
                    truncated = len(description) > max_length
                    display_text = description if not truncated else description[:max_length] + "..."
                    
                    desc_label = QLabel(display_text)
                    desc_label.setStyleSheet("color: #cccccc; font-size: 12px;")
                    desc_label.setWordWrap(True)
                    desc_container_layout.addWidget(desc_label)
                    
                    # Add "Show more" indicator if truncated
                    if truncated:
                        show_more = QLabel("Click to expand...")
                        show_more.setStyleSheet("color: #0078d4; font-size: 11px; font-style: italic;")
                        desc_container_layout.addWidget(show_more)
                    
                    # Make the container clickable
                    desc_container.mousePressEvent = lambda event, container=desc_container, label=desc_label, full_text=description: self.toggle_description(container, label, full_text)
                    
                    # Store if currently expanded
                    desc_container.is_expanded = False
                    
                    details_layout.addWidget(desc_container)
                
                title_section.addWidget(details_frame)
            
            header.addLayout(title_section, 1)  # Give title section more space
            
            # Status section
            status_section = QHBoxLayout()
            status_section.setSpacing(8)
            
            status_combo = QComboBox()
            status_combo.addItems(["New", "In Progress", "Completed", "Needs Info"])
            current_status = opportunity.display_status if hasattr(opportunity, 'display_status') else opportunity.status.title()
            status_combo.setCurrentText(current_status)
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
            
            # Protect from accidental wheel scrolling
            self.protect_combobox_from_wheel(status_combo)
            
            status_combo.setProperty("opportunity", opportunity)
            status_combo.currentTextChanged.connect(self.handle_status_change)
            status_section.addWidget(status_combo)
            
            header.addLayout(status_section)
            card_layout.addLayout(header)
            
            # Buttons section (comment, view details)
            buttons_layout = QHBoxLayout()
            buttons_layout.setSpacing(8)
            
            # View Details button
            if opportunity.description or opportunity.systems:
                view_btn = QPushButton("View Details")
                view_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #262626;
                        color: #0078d4;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 12px;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #333333;
                        color: #2196F3;
                    }
                """)
                view_btn.clicked.connect(lambda checked, o=opportunity: self.focus_ticket(o.id))
                buttons_layout.addWidget(view_btn)
            
            # Comments button
            if hasattr(opportunity, 'comments') and opportunity.comments:
                comments_btn = QPushButton(f"Comments ({len(opportunity.comments)})")
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
                }
                QPushButton:hover {
                    background-color: #333333;
                    color: #2196F3;
                }
            """)
            comments_btn.clicked.connect(lambda checked, o=opportunity: self.show_comments_dialog(o))
            buttons_layout.addWidget(comments_btn)
            
            buttons_layout.addStretch()
            
            if not self.is_compact:
                card_layout.addLayout(buttons_layout)
            
            card.setLayout(card_layout)
            self.opportunities_layout.addWidget(card)
            return card
        
        except Exception as e:
            print(f"ERROR creating opportunity widget: {str(e)}")
            print("Traceback:", traceback.format_exc())
            return None

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

    def protect_combobox_from_wheel(self, combobox: QComboBox) -> None:
        """Install event filter to protect combobox from accidental wheel scrolling"""
        class ComboBoxEventFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Wheel and not obj.hasFocus():
                    # Block wheel events when combo box doesn't have focus
                    return True
                return False
        
        # Create and install the event filter
        event_filter = ComboBoxEventFilter()
        combobox.installEventFilter(event_filter)
        # Store reference to prevent garbage collection
        combobox.event_filter = event_filter

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
        refresh_btn.clicked.connect(lambda: self.load_opportunities(show_refresh_animation=True))
        title_row.addWidget(refresh_btn, alignment=Qt.AlignRight)
        header_layout.addLayout(title_row)
        
        # Filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        
        filter_buttons = [
            ("Active Tickets", "active_tickets"),
            ("My Tickets", "my_tickets"),
            ("New", "new"),
            ("In Progress", "in_progress"),
            ("Completed", "completed"),
            ("Needs Info", "needs_info")
        ]
        
        # Store filter buttons to access them later
        self.filter_buttons = {}
        
        for label, filter_id in filter_buttons:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(filter_id == self.current_filter)  # Use current_filter to determine which button is checked
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
            self.filter_buttons[filter_id] = btn
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
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addDays(-30))  # Default to 30 days ago
        date_layout.addWidget(self.from_date)
        date_layout.addWidget(QLabel("to"))
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate().addDays(1))  # Include today and tomorrow
        date_layout.addWidget(self.to_date)
        advanced_filter_layout.addLayout(date_layout)
        
        # Add field for "My Tickets" filter type selection
        self.my_tickets_filter_type = QComboBox()
        self.my_tickets_filter_type.addItem("Created")
        self.my_tickets_filter_type.addItem("Assigned")
        self.my_tickets_filter_type.addItem("Both")
        self.my_tickets_filter_type.currentTextChanged.connect(self.filter_opportunities)
        
        # Create container for My Tickets specific filters
        self.my_tickets_filters = QWidget()
        my_tickets_layout = QHBoxLayout(self.my_tickets_filters)
        my_tickets_layout.setSpacing(16)
        
        # Add the filter type to the My Tickets filters
        my_tickets_layout.addWidget(QLabel("Show:"))
        my_tickets_layout.addWidget(self.my_tickets_filter_type)
        
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
        # Protect from accidental wheel scrolling
        self.protect_combobox_from_wheel(self.status_filter)
        
        my_tickets_layout.addWidget(QLabel("Status:"))
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
        self.assignment_filter.addItem("Created By Me")
        self.assignment_filter.addItem("Assigned To Me")
        self.assignment_filter.addItem("Unassigned")
        self.assignment_filter.currentTextChanged.connect(self.filter_opportunities)
        # Protect from accidental wheel scrolling
        self.protect_combobox_from_wheel(self.assignment_filter)
        
        my_tickets_layout.addWidget(QLabel("Assignment:"))
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
        
        # Flag for tracking if advanced filters are applied
        self.advanced_filter_applied = False
        
        # Initially hide the advanced filter frame
        self.advanced_filter_frame.setVisible(False)
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

    def do_refresh(self, show_refresh_animation=False):
        """Actually perform the refresh
        
        Args:
            show_refresh_animation: Whether to show the refresh animation
        """
        if self.is_loading:
            return
            
        self.is_loading = True
        
        # Only show refresh animation when explicitly requested
        if show_refresh_animation:
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
                    # Check status using normalized_status property
                    if hasattr(opp, 'normalized_status') and opp.normalized_status == "new":
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
            
            # Only show refresh confirmation when animation was shown
            if show_refresh_animation:
                self.hide_refresh_animation()

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
                background-color: rgba(30, 30, 30, {int(220 * self.fade_opacity)});
                border-radius: 4px;
                padding: 6px 10px;
            }}
        """)

    def load_opportunities(self, show_refresh_animation=False):
        """Load opportunities based on current filter
        
        Args:
            show_refresh_animation: Whether to show the refresh animation
                                   True when triggered by refresh button,
                                   False during initial load or other automatic calls
        """
        if self.is_loading:
            return
            
        self.is_loading = True
        
        # Only show refresh animation when explicitly requested (e.g., from refresh button)
        if show_refresh_animation:
            self.show_refresh_animation()
        
        try:
            # Clear existing widgets
            self.cleanup_widgets()
            
            # Extra debug - print current filter and UI state
            print(f"\nDEBUG: Loading opportunities with filter '{self.current_filter}'")
            print(f"DEBUG: Current UI buttons checked state:")
            if hasattr(self, 'filter_buttons'):
                for filter_id, btn in self.filter_buttons.items():
                    print(f"  {filter_id}: {btn.isChecked()}")
                    
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
                    
                    # For all new status items visible in any view
                    for opp in opportunities:
                        # Check status using normalized_status property
                        if hasattr(opp, 'normalized_status') and opp.normalized_status == "new":
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
                self._last_error = str(e)
                print(f"Error loading opportunities: {str(e)}")
                print(traceback.format_exc())
            finally:
                db.close()
                
        finally:
            self.is_loading = False
            
            # Only show refresh confirmation when animation was shown
            if show_refresh_animation:
                self.hide_refresh_animation()
    
    def apply_filter(self, filter_id):
        """Apply filter and reload opportunities"""
        # Update filter buttons visual state
        for button in self.findChildren(QPushButton):
            if hasattr(button, 'property') and button.property("filter_id"):
                button.setChecked(button.property("filter_id") == filter_id)
        
        self.current_filter = filter_id
        print(f"DEBUG: Changed filter to '{filter_id}'")
        
        # Show/hide advanced filter frame and My Tickets specific filters
        self.advanced_filter_frame.setVisible(True)  # Always show advanced filter frame
        self.my_tickets_filters.setVisible(filter_id == "my_tickets")  # Only show My Tickets specific filters for my_tickets
        
        # Reset advanced filter flag when changing filters
        self.advanced_filter_applied = False
        
        self.load_opportunities()

    def filter_opportunities(self):
        """Filter opportunities based on status and assignment filters"""
        self.load_opportunities()

    def apply_advanced_filters(self):
        """Apply advanced filters"""
        # Set a flag to indicate advanced filters were explicitly applied
        self.advanced_filter_applied = True
        self.load_opportunities()

    def reset_filters(self):
        """Reset advanced filters to default values"""
        # Set date range to last 30 days instead of 7 days to include more recent tickets
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.to_date.setDate(QDate.currentDate().addDays(1))  # Include today and tomorrow to ensure all recent tickets show
        
        if self.current_filter == "my_tickets":
            self.status_filter.setCurrentText("")
            self.assignment_filter.setCurrentText("")
            self.my_tickets_filter_type.setCurrentText("Created")
        
        # Reset the advanced filter flag
        self.advanced_filter_applied = False
        self.apply_advanced_filters()
    
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
        self.current_filter = "active_tickets"  # Switch to all tickets view
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

    def open_attachment(self, file):
        """Open or download an attachment file"""
        try:
            import subprocess
            import platform
            import tempfile
            
            # Get file extension to determine viewer
            file_ext = os.path.splitext(file.display_name)[1].lower()
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
            pdf_extensions = {'.pdf'}
            
            # Determine file path
            temp_file_path = None
            
            if file.storage_path.startswith('local'):
                # Local storage
                storage_path = file.storage_path.replace('local/', '')
                full_path = os.path.join(STORAGE_DIR, storage_path)
                
                # Check if file exists
                if not os.path.exists(full_path):
                    QMessageBox.warning(
                        self, 
                        "File Not Found", 
                        f"The file '{file.display_name}' could not be found at:\n{full_path}"
                    )
                    return
                    
                final_path = full_path
                
            else:
                # Remote storage (Supabase) - download to temp location
                print(f"Downloading remote file: {file.storage_path}")
                try:
                    temp_file_path = SupabaseStorageService.download_file(file.storage_path)
                    if not temp_file_path:
                        # If download fails, try to get a download URL
                        file_url = SupabaseStorageService.get_file_url(file.storage_path, expires_in=3600)
                        if file_url:
                            QMessageBox.information(
                                self,
                                "File Access",
                                f"File: {file.display_name}\n\n"
                                f"The file could not be downloaded directly.\n"
                                f"You can download it from this URL:\n\n{file_url}\n\n"
                                f"(Link expires in 1 hour)"
                            )
                            return
                        else:
                            QMessageBox.warning(
                                self,
                                "File Access Error",
                                f"Unable to access file: {file.display_name}\n\n"
                                f"The file could not be opened or downloaded from cloud storage."
                            )
                            return
                    final_path = temp_file_path
                    
                except Exception as remote_error:
                    print(f"Error accessing remote file: {remote_error}")
                    QMessageBox.critical(
                        self,
                        "Remote File Error",
                        f"Error accessing file: {file.display_name}\n\n"
                        f"Error: {str(remote_error)}"
                    )
                    return
            
            # Open with appropriate viewer
            if file_ext in image_extensions:
                # Open with built-in image viewer
                try:
                    viewer = ImageViewerDialog(final_path, file.display_name, self)
                    viewer.exec_()
                    # Clean up temp file if it was downloaded
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass  # Ignore cleanup errors
                    return
                except Exception as e:
                    print(f"Error opening image viewer: {e}")
                    # Fall back to external viewer
                    
            elif file_ext in pdf_extensions:
                # Open with built-in PDF viewer
                try:
                    viewer = PDFViewerDialog(final_path, file.display_name, self)
                    viewer.exec_()
                    # Clean up temp file if it was downloaded
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass  # Ignore cleanup errors
                    return
                except Exception as e:
                    print(f"Error opening PDF viewer: {e}")
                    # Fall back to external viewer
            
                        # Fallback: Open with external application
            try:
                if platform.system() == 'Windows':
                    os.startfile(final_path)
                elif platform.system() == 'Darwin':  # macOS
                    subprocess.run(['open', final_path])
                else:  # Linux
                    subprocess.run(['xdg-open', final_path])
                    
                print(f"Opened file with external application: {final_path}")
                
                # Clean up temp file if it was downloaded
                if temp_file_path and os.path.exists(temp_file_path):
                    # Delay cleanup to allow external app to load the file
                    QTimer.singleShot(5000, lambda: self.cleanup_temp_file(temp_file_path))
                
            except Exception as e:
                # If opening fails, show file info and offer to copy path
                reply = QMessageBox.question(
                    self,
                    "Unable to Open File",
                    f"Could not open '{file.display_name}' with default application.\n\n"
                    f"File path: {final_path}\n\n"
                    f"Would you like to copy the file path to clipboard?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    try:
                        from PyQt5.QtWidgets import QApplication
                        clipboard = QApplication.clipboard()
                        clipboard.setText(final_path)
                        QMessageBox.information(self, "Copied", "File path copied to clipboard!")
                    except Exception as clip_error:
                        print(f"Error copying to clipboard: {clip_error}")
                
                # Clean up temp file on error
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                        
        except Exception as e:
            print(f"Error opening attachment: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while trying to open the file:\n{str(e)}"
            )
    
    def cleanup_temp_file(self, temp_file_path):
        """Clean up a temporary file"""
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                print(f"Cleaned up temporary file: {temp_file_path}")
        except Exception as e:
            print(f"Error cleaning up temporary file {temp_file_path}: {e}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Override close event to hide the dashboard instead of closing the application"""
        print("DEBUG: Dashboard close event triggered")
        # Instead of accepting the close event (which would close the widget),
        # we hide it and ignore the event
        self.hide()
        event.ignore()

    def toggle_description(self, container, label, full_text):
        """Toggle between truncated and full text in description"""
        if not hasattr(container, 'is_expanded'):
            container.is_expanded = False
            
        if container.is_expanded:
            # Contract: Show truncated text
            max_length = 150
            truncated = len(full_text) > max_length
            display_text = full_text if not truncated else full_text[:max_length] + "..."
            label.setText(display_text)
            
            # Update show more indicator if needed
            if truncated:
                # Find and update the show more indicator
                for i in range(container.layout().count()):
                    widget = container.layout().itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget != label:
                        widget.setText("Click to expand...")
                        widget.show()
            
            container.is_expanded = False
        else:
            # Expand: Show full text
            label.setText(full_text)
            
            # Hide the show more indicator
            for i in range(container.layout().count()):
                widget = container.layout().itemAt(i).widget()
                if isinstance(widget, QLabel) and widget != label:
                    widget.setText("Click to collapse...")
            
            container.is_expanded = True
            
        # Adjust layout as needed
        container.adjustSize()
        self.opportunities_container.adjustSize()
        
    def show_details_dialog(self, title, description):
        """Show a dialog with the full text of a description"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Full Details")
        dialog.setMinimumSize(600, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
            QTextEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 8px;
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
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(16)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Description in a text edit (readonly)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(description)
        text_edit.setStyleSheet("font-size: 13px;")
        layout.addWidget(text_edit)
        
        # Close button
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.exec_()

class ImageViewerDialog(QDialog):
    def __init__(self, file_path, file_name, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = file_name
        self.zoom_factor = 1.0
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle(f"Image Viewer - {self.file_name}")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        # Zoom controls
        zoom_out_btn = QPushButton("Zoom Out (-)")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_out_btn.setStyleSheet("""
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
        toolbar.addWidget(zoom_out_btn)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet("color: white; font-weight: bold; margin: 0 10px;")
        toolbar.addWidget(self.zoom_label)
        
        zoom_in_btn = QPushButton("Zoom In (+)")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_in_btn.setStyleSheet(zoom_out_btn.styleSheet())
        toolbar.addWidget(zoom_in_btn)
        
        fit_btn = QPushButton("Fit to Window")
        fit_btn.clicked.connect(self.fit_to_window)
        fit_btn.setStyleSheet(zoom_out_btn.styleSheet())
        toolbar.addWidget(fit_btn)
        
        actual_size_btn = QPushButton("Actual Size")
        actual_size_btn.clicked.connect(self.actual_size)
        actual_size_btn.setStyleSheet(zoom_out_btn.styleSheet())
        toolbar.addWidget(actual_size_btn)
        
        toolbar.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #d83b01;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ea4a1f;
            }
        """)
        toolbar.addWidget(close_btn)
        
        layout.addLayout(toolbar)
        
        # Scroll area for image
        self.scroll_area = QScrollArea()
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
            }
        """)
        
        # Image label
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #2d2d2d;")
        
        # Load and display image
        self.original_pixmap = QPixmap(self.file_path)
        if self.original_pixmap.isNull():
            self.image_label.setText("Failed to load image")
            self.image_label.setStyleSheet("color: white; font-size: 16px;")
        else:
            self.update_image()
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
        """)
        
        # Fit to window initially
        if not self.original_pixmap.isNull():
            QTimer.singleShot(100, self.fit_to_window)
    
    def update_image(self):
        if not self.original_pixmap.isNull():
            scaled_pixmap = self.original_pixmap.scaled(
                self.original_pixmap.size() * self.zoom_factor,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.resize(scaled_pixmap.size())
            self.zoom_label.setText(f"{int(self.zoom_factor * 100)}%")
    
    def zoom_in(self):
        if self.zoom_factor < 5.0:
            self.zoom_factor *= 1.25
            self.update_image()
    
    def zoom_out(self):
        if self.zoom_factor > 0.1:
            self.zoom_factor /= 1.25
            self.update_image()
    
    def actual_size(self):
        self.zoom_factor = 1.0
        self.update_image()
    
    def fit_to_window(self):
        if not self.original_pixmap.isNull():
            # Calculate zoom factor to fit image in scroll area
            scroll_size = self.scroll_area.size()
            image_size = self.original_pixmap.size()
            
            # Account for scroll bars
            available_width = scroll_size.width() - 20
            available_height = scroll_size.height() - 20
            
            width_ratio = available_width / image_size.width()
            height_ratio = available_height / image_size.height()
            
            self.zoom_factor = min(width_ratio, height_ratio, 1.0)  # Don't zoom in beyond actual size
            self.update_image()

class PDFViewerDialog(QDialog):
    def __init__(self, file_path, file_name, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_name = file_name
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle(f"PDF Viewer - {self.file_name}")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel(f"PDF File: {self.file_name}")
        info_label.setStyleSheet("""
            color: white;
            font-size: 16px;
            font-weight: bold;
            padding: 10px;
            background-color: #2d2d2d;
            border-radius: 4px;
            margin-bottom: 10px;
        """)
        layout.addWidget(info_label)
        
        # PDF info
        pdf_info = QTextEdit()
        pdf_info.setReadOnly(True)
        pdf_info.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        
        # Get file info
        file_size = os.path.getsize(self.file_path)
        size_mb = file_size / (1024 * 1024)
        
        info_text = f"""PDF Document Information:

File: {self.file_name}
Size: {size_mb:.2f} MB
Path: {self.file_path}

This PDF can be opened with your default PDF viewer using the button below.

Note: Full PDF rendering within the application requires additional dependencies.
For now, you can view basic file information and open with external viewer."""
        
        pdf_info.setPlainText(info_text)
        layout.addWidget(pdf_info)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        open_external_btn = QPushButton("Open with Default PDF Viewer")
        open_external_btn.clicked.connect(self.open_external)
        open_external_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        button_layout.addWidget(open_external_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #d83b01;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #ea4a1f;
            }
        """)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
        """)
    
    def open_external(self):
        """Open PDF with external application"""
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == 'Windows':
                os.startfile(self.file_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', self.file_path])
            else:  # Linux
                subprocess.run(['xdg-open', self.file_path])
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Could not open PDF with external viewer:\n{str(e)}"
            )

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
        if self.new_status == "Needs Info" and not self.comment:
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