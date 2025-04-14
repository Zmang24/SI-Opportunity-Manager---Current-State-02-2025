import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QPushButton, QLabel, QStackedWidget, QSystemTrayIcon,
                           QMenu, QStyle, QHBoxLayout, QFrame, QSlider, QDialog, QMessageBox)
from PyQt5.QtCore import Qt, QSize, QPoint, QTimer, QSettings
from PyQt5.QtGui import (QIcon, QPixmap, QImage, QTransform, QPainter, QColor, QLinearGradient,
                      QPaintEvent, QMouseEvent, QResizeEvent, QMoveEvent, QCloseEvent)
from app.ui.qt_types import (
    AlignCenter, FramelessWindowHint, WindowStaysOnTopHint, Tool, NoDropShadowWindowHint,
    WA_TranslucentBackground, WA_ShowWithoutActivating, WA_AlwaysShowToolTips,
    Horizontal, Vertical, SmoothTransformation, KeepAspectRatio, IgnoreAspectRatio,
    NoPen, WindowMinimized, AA_EnableHighDpiScaling, AA_UseHighDpiPixmaps,
    AA_UseStyleSheetPropagationInWidgetStyles, AA_DontCreateNativeWidgetSiblings
)
from app.ui.dashboard import DashboardWidget
from app.ui.opportunity_form import OpportunityForm
from app.ui.auth import AuthWidget
from app.ui.account_creation import AccountCreationWidget
from app.ui.settings import SettingsWidget
from app.ui.management_portal import ManagementPortal
from app.ui.profile import ProfileWidget
from app.ui.notifications import notification_manager
from app.database.connection import SessionLocal
from app.models.models import Opportunity, Notification, User
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # Import ZoneInfo for more robust timezone handling
from sqlalchemy import and_, or_, text
import traceback
from typing import Optional, Dict, List, Union, cast, Any, Protocol, TypeVar, TYPE_CHECKING
import asyncio
import json
from app.utils.dependency_checker import check_dependencies

T = TypeVar('T')

if TYPE_CHECKING:
    from PyQt5.QtCore import QObject
    from PyQt5.QtWidgets import QWidget as QWidgetType

class DatabaseSession(Protocol):
    def query(self, model: type[T]) -> 'Query[T]': ...
    def add(self, obj: Any) -> None: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...

class Query(Protocol[T]):
    def filter(self, *criterion: Any) -> 'Query[T]': ...
    def first(self) -> Optional[T]: ...
    def all(self) -> list[T]: ...

class NotificationBadge(QLabel):
    """A badge showing the number of unread notifications"""
    def __init__(self, parent: Optional['QWidgetType'] = None) -> None:
        super().__init__(parent)
        self.setAlignment(AlignCenter)
        self.setAttribute(WA_TranslucentBackground)
        
        # Slightly larger size for better visibility
        self.setFixedSize(22, 22)
        
        # Modern style with gradient background and refined typography
        self.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF4B4B,
                    stop:1 #FF6B6B);
                color: white;
                border-radius: 11px;
                padding: 0px;
                font-size: 11px;
                font-weight: 600;
                font-family: 'Segoe UI', Arial, sans-serif;
                margin: 0px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        print("DEBUG: NotificationBadge created with size:", self.size())

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the notification badge with custom styling"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw red circle background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 0, 0))
        painter.drawEllipse(0, 0, self.width(), self.height())
        
        # Draw notification count text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect(), AlignCenter, self.text())

class DragHandle(QWidget):
    def __init__(self, parent: Optional['QWidgetType'] = None, orientation: Qt.Orientation = Qt.Horizontal) -> None:
        super().__init__(parent)
        self._orientation = orientation
        self.setFixedSize(8, 30 if orientation == Qt.Horizontal else 8)
        self.setCursor(Qt.SizeHorCursor if orientation == Qt.Horizontal else Qt.SizeVerCursor)
        
        # Style with a semi-transparent background
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(43, 43, 43, 0.95);
                border-radius: 5px;
            }
            QWidget:hover {
                background-color: rgba(60, 60, 60, 0.95);
            }
        """)
        
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw handle dots
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        
        if self._orientation == Qt.Horizontal:
            # Draw three horizontal dots
            for i in range(3):
                painter.drawEllipse(2, 8 + i * 7, 4, 4)
        else:
            # Draw three vertical dots
            for i in range(3):
                painter.drawEllipse(8 + i * 7, 2, 4, 4)

class PeekButton(QPushButton):
    def __init__(self, parent: Optional['QWidgetType'] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setCursor(Qt.PointingHandCursor)
        self._expanded = False
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 15px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.setText("◀")  # Left arrow for collapsed state

    def toggle_state(self, is_expanded: bool) -> None:
        """Toggle the peek button state"""
        self._expanded = is_expanded
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the peek button with custom styling"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw arrow
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        
        if self._expanded:
            points = [QPoint(4, 12), QPoint(12, 12), QPoint(8, 4)]
        else:
            points = [QPoint(4, 4), QPoint(12, 4), QPoint(8, 12)]
            
        painter.drawPolygon(*points)

class FloatingToolbar(QWidget):
    def __init__(self, parent: Optional['QWidgetType'] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.NoDropShadowWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_AlwaysShowToolTips)
        
        # Enable mouse tracking for the toolbar itself
        self.setMouseTracking(True)
        
        # Load background image
        self.bg_image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'resources', 'icons', 'Brushed_Bar_horizontal.png')
        self.background_image = QPixmap(self.bg_image_path)
        
        self.is_vertical = True  # Always start in vertical mode
        self.settings = QSettings('SI Opportunity Manager', 'Toolbar')
        self.initUI()
        self.is_pinned = False
        self.drag_position = None
        self.notification_count = 0
        
        # Initialize with ZoneInfo for more robust timezone handling
        try:
            utc = ZoneInfo('UTC')
            print("DEBUG: Using ZoneInfo for timezone handling")
            current_time = datetime.now(utc)
            self.last_checked_time = current_time - timedelta(minutes=5)
            self.last_reminder_time = current_time  # Initialize last reminder time
            print(f"DEBUG: Initialized last_checked_time to {self.last_checked_time}")
            print(f"DEBUG: Initialized last_reminder_time to {self.last_reminder_time}")
        except Exception as e:
            print(f"DEBUG: Error initializing timezone with ZoneInfo, falling back to standard timezone: {str(e)}")
            # Fallback to standard timezone if ZoneInfo is not available
            self.last_checked_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            self.last_reminder_time = datetime.now(timezone.utc)
            
        self.viewed_opportunities = set()
        self.viewed_notifications = set()
        
        # Load last position or set default
        self.load_position()
        
        # Add color animation properties
        self.current_hue = 0.0
        self.color_timer = QTimer(self)
        self.color_timer.timeout.connect(self.update_icon_colors)
        
        # Store original colors for non-animating buttons
        self.static_colors = {
            "new": "#00FF00",  # Keep green
            "close": "#FF0000"  # Keep red
        }
        
        # Initialize with user's theme if available, otherwise use default
        self.current_theme = "Rainbow Animation"
        
        # Load user's theme preference if parent has a current_user with icon_theme
        if parent and hasattr(parent, 'current_user') and hasattr(parent.current_user, 'icon_theme') and parent.current_user.icon_theme:
            print(f"Loading user's theme preference: {parent.current_user.icon_theme}")
            self.current_theme = parent.current_user.icon_theme
            
        # Apply the theme
        if self.current_theme == "Rainbow Animation":
            self.color_timer.start(50)  # Start with rainbow animation
        else:
            # Apply static theme
            print(f"Applying user's saved theme: {self.current_theme}")
            self.apply_static_theme()

        # Initialize notification check timer
        print("DEBUG: Initializing notification check timer")
        self.notification_timer = QTimer(self)
        self.notification_timer.timeout.connect(self.check_updates)
        check_interval = 30000  # Check every 30 seconds (30000 ms)
        print(f"DEBUG: Starting notification timer with interval of {check_interval}ms")
        self.notification_timer.start(check_interval)
        print("DEBUG: Notification timer started")
        
        # Run an immediate check after initialization
        QTimer.singleShot(2000, lambda: self.check_updates())
        print("DEBUG: Scheduled immediate update check after 2 seconds")

    def initUI(self):
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Create container frame
        self.container = QFrame()
        self.container.setObjectName("toolbar_container")
        self.container.setStyleSheet("""
            QFrame#toolbar_container {
                border: none;
                min-width: 36px;
                max-width: 36px;
                min-height: 460px;
                padding: 0px;
                margin: 0px;
                background-color: transparent;
            }
        """)
        
        # Container layout
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)
        
        # Create buttons
        icons_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                 'resources', 'icons')
        
        buttons_data = [
            ("new", "new-svgrepo-com.svg", "#00FF00", "Create New Ticket"),  # Green
            ("dashboard", "dashboard-gauge-measure-svgrepo-com.svg", "#FFFFFF", "View Dashboard"),  # White
            ("management", "manager-avatar-svgrepo-com.svg", "#FFFFFF", "Management Portal"),
            ("profile", "profile-default-svgrepo-com.svg", "#FFFFFF", "User Profile"),
            ("pin", "Anchor for Pin toggle.svg", "#FFFFFF", "Pin Toolbar"),
            ("layout", "Veritical to Horizontal.svg", "#FFFFFF", "Toggle Layout"),
            ("opacity", "eye-svgrepo-com.svg", "#FFFFFF", "Adjust Opacity"),
            ("close", "exit-sign-svgrepo-com.svg", "#FF0000", "Exit Application")  # Red
        ]

        self.buttons = {}
        for btn_id, icon_file, icon_color, tooltip in buttons_data:
            print(f"\nDEBUG: Processing button {btn_id}")
            # Skip management button if user is not admin/manager
            if btn_id == "management":
                parent = self.parent()
                print(f"DEBUG: Management button check - Parent: {parent}, Current user: {parent.current_user if parent else None}")
                if not parent or not parent.current_user:
                    print("DEBUG: Skipping management button - No parent or current user")
                    continue
                print(f"DEBUG: User role: {parent.current_user.role}")
                if parent.current_user.role.lower() not in ["admin", "manager"]:
                    print(f"DEBUG: Skipping management button - User role not admin/manager")
                    continue
                print("DEBUG: Adding management button")
                
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setMouseTracking(True)
            btn.setAttribute(Qt.WA_AlwaysShowToolTips)
            btn.setToolTip(tooltip)
            
            # Set button style with updated tooltip styling
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(43, 43, 43, 0.25);
                    border: none;
                    padding: 0px;
                    margin: 0px;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: rgba(60, 60, 60, 0.35);
                }
                QPushButton:pressed {
                    background-color: rgba(30, 30, 30, 0.45);
                }
            """)
            
            # Set global tooltip style
            self.setStyleSheet("""
                QToolTip {
                    background-color: rgba(43, 43, 43, 0.95);
                    color: white;
                    border: 1px solid #555555;
                    padding: 5px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin: 0px;
                }
            """)
            
            # Load and set SVG icon
            icon_path = os.path.join(icons_path, icon_file)
            if os.path.exists(icon_path):
                print(f"DEBUG: Loading icon from {icon_path}")
                icon_pixmap = QPixmap(icon_path)
                
                # Convert icon to specified color
                temp_image = icon_pixmap.toImage()
                for x in range(temp_image.width()):
                    for y in range(temp_image.height()):
                        color = temp_image.pixelColor(x, y)
                        if color.alpha() > 0:
                            new_color = QColor(icon_color)
                            new_color.setAlpha(color.alpha())
                            temp_image.setPixelColor(x, y, new_color)
                icon_pixmap = QPixmap.fromImage(temp_image)
                
                # Scale icon to proper size (24x24)
                scaled_pixmap = icon_pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                btn.setIcon(QIcon(scaled_pixmap))
                btn.setIconSize(QSize(24, 24))
            else:
                print(f"DEBUG: Icon file not found: {icon_path}")
            
            # Connect button signals
            if btn_id == "new":
                btn.clicked.connect(lambda: self.parent().show_opportunity_form() if self.parent() and self.parent().current_user else None)
            elif btn_id == "dashboard":
                btn.clicked.connect(lambda: self.parent().show_dashboard() if self.parent() and self.parent().current_user else None)
                # Create and configure notification badge
                self.dashboard_badge = NotificationBadge(btn)
                # Position the badge in the top-right corner with adjusted position
                self.dashboard_badge.move(15, -5)
                self.dashboard_badge.hide()
                self.dashboard_badge.raise_()
                print("DEBUG: Dashboard badge initialized at position:", self.dashboard_badge.pos())
                
                # Add right-click menu for dashboard button to reset notifications
                btn.setContextMenuPolicy(Qt.CustomContextMenu)
                btn.customContextMenuRequested.connect(self.show_dashboard_menu)
            elif btn_id == "management":
                btn.clicked.connect(lambda: self.parent().show_management_portal() if self.parent() and self.parent().current_user else None)
            elif btn_id == "profile":
                btn.clicked.connect(lambda: self.parent().show_profile() if self.parent() and self.parent().current_user else None)
            elif btn_id == "pin":
                btn.clicked.connect(self.toggle_pin)
                self.pin_button = btn
            elif btn_id == "layout":
                btn.clicked.connect(self.toggle_layout)
                self.layout_button = btn
            elif btn_id == "opacity":
                btn.clicked.connect(self.show_opacity_slider)
            elif btn_id == "close":
                btn.clicked.connect(QApplication.quit)
            
            self.buttons[btn_id] = btn
            print(f"DEBUG: Added button {btn_id} to buttons dictionary")
            self.container_layout.addWidget(btn, 0, Qt.AlignCenter)
        
        # Add container to main layout
        self.main_layout.addWidget(self.container, 0, Qt.AlignCenter)
        
        # Set fixed width for toolbar
        self.setFixedWidth(36)
        self.setMinimumHeight(460)

    def paintEvent(self, event):
        """Custom paint event to draw the metallic background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background image if it exists
        if hasattr(self, 'background_image') and not self.background_image.isNull():
            # Scale and transform the background image based on orientation
            if self.is_vertical:
                transformed_image = self.background_image.transformed(QTransform().rotate(90))
                scaled_image = transformed_image.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            else:
                scaled_image = self.background_image.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(self.rect(), scaled_image)
        else:
            # Fallback to gradient if image is not available
            gradient = QLinearGradient(0, 0, self.width(), 0)
            gradient.setColorAt(0, QColor(30, 30, 30))
            gradient.setColorAt(0.5, QColor(45, 45, 45))
            gradient.setColorAt(1, QColor(30, 30, 30))
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(self.rect(), 2, 2)
            
            # Add subtle highlight at the top
            highlight = QLinearGradient(0, 0, 0, 10)
            highlight.setColorAt(0, QColor(255, 255, 255, 20))
            highlight.setColorAt(1, QColor(255, 255, 255, 0))
            painter.setBrush(highlight)
            painter.drawRect(0, 0, self.width(), 10)
            
            # Add subtle shadow at the bottom
            shadow = QLinearGradient(0, self.height() - 10, 0, self.height())
            shadow.setColorAt(0, QColor(0, 0, 0, 0))
            shadow.setColorAt(1, QColor(0, 0, 0, 40))
            painter.setBrush(shadow)
            painter.drawRect(0, self.height() - 10, self.width(), 10)

    def load_position(self):
        """Load the last saved position or set default position"""
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Set size for vertical layout
        self.setFixedWidth(36)
        self.setMinimumHeight(460)
        self.resize(36, 460)
        
        # Position at right-center by default
        self.move(
            screen.width() - self.width() - 10,
            (screen.height() - self.height()) // 2
        )
        
        # Load saved position if available
        saved_pos = self.settings.value('toolbar_position', None)
        if saved_pos and isinstance(saved_pos, list) and len(saved_pos) == 2:
            try:
                x, y = int(saved_pos[0]), int(saved_pos[1])
                if self.is_position_valid(QPoint(x, y)):
                    self.move(x, y)
            except (ValueError, TypeError):
                pass

    def is_position_valid(self, pos):
        """Check if the given position is valid (visible on any screen)"""
        for screen in QApplication.screens():
            if screen.availableGeometry().contains(pos):
                return True
        return False

    def save_position(self):
        """Save the current position"""
        pos = self.pos()
        self.settings.setValue('toolbar_position', [int(pos.x()), int(pos.y())])
        self.settings.sync()  # Ensure settings are saved immediately

    def toggle_peek(self):
        """Toggle between peeked and expanded states in vertical mode"""
        if not self.is_vertical:
            return
            
        self.is_peeked = not self.is_peeked
        
        if self.is_peeked:
            # Collapse to peek state
            self.container.hide()
            self.handle.hide()
            self.setFixedWidth(30)
            self.peek_button.move(0, self.height() // 2 - 15)
            self.peek_button.toggle_state(False)
            self.peek_button.raise_()  # Ensure peek button stays on top
        else:
            # Expand to full state
            self.setFixedWidth(90)  # Match container width
            self.container.show()
            self.handle.show()
            self.peek_button.move(60, self.height() // 2 - 15)  # Adjusted position
            self.peek_button.toggle_state(True)
            self.peek_button.raise_()  # Ensure peek button stays on top

    def toggle_layout(self):
        """Toggle between vertical and horizontal layout"""
        self.is_vertical = not self.is_vertical
        
        # Reset peek state when switching layouts
        self.is_peeked = False
        
        # Get the layout button's icon
        if hasattr(self, 'layout_button'):
            icon = self.layout_button.icon()
            if not icon.isNull():
                pixmap = icon.pixmap(24, 24)
                
        if self.is_vertical:
            # Rotate the layout icon 90 degrees for vertical mode
            if hasattr(self, 'layout_button'):
                transform = QTransform().rotate(90)
                rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
                self.layout_button.setIcon(QIcon(rotated_pixmap))
            
            # Set vertical layout dimensions
            self.setFixedWidth(36)
            self.setMinimumHeight(460)
            self.container.setStyleSheet("""
                QFrame#toolbar_container {
                    border: none;
                    min-width: 36px;
                    max-width: 36px;
                    min-height: 460px;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
                }
            """)
            
            # Create new vertical layout with no spacing
            new_layout = QVBoxLayout()
            new_layout.setContentsMargins(0, 0, 0, 0)
            new_layout.setSpacing(0)
            
            # Update button sizes for vertical layout
            for btn in self.buttons.values():
                btn.setFixedSize(36, 36)
                btn.setIconSize(QSize(24, 24))
                
                # Update button style with increased transparency
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(43, 43, 43, 0.25);
                        border: none;
                        padding: 0px;
                        margin: 0px;
                        border-radius: 8px;
                    }
                    QPushButton:hover {
                        background-color: rgba(60, 60, 60, 0.35);
                    }
                    QPushButton:pressed {
                        background-color: rgba(30, 30, 30, 0.45);
                    }
                """)
        else:
            # Reset layout icon rotation for horizontal mode
            if hasattr(self, 'layout_button'):
                self.layout_button.setIcon(QIcon(pixmap))
            
            # Set horizontal layout dimensions
            self.setFixedHeight(56)  # Reduced height to better fit background
            self.setMinimumWidth(650)  # Adjusted minimum width
            self.container.setStyleSheet("""
                QFrame#toolbar_container {
                    border: none;
                    min-height: 56px;
                    max-height: 56px;
                    min-width: 650px;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
                }
            """)
            
            # Create new horizontal layout with adjusted margins
            new_layout = QHBoxLayout()
            new_layout.setContentsMargins(80, 2, 80, 2)  # Reduced margins
            new_layout.setSpacing(8)  # Increased spacing between buttons
            
            # Update button sizes for horizontal layout
            for btn in self.buttons.values():
                btn.setFixedSize(48, 48)  # Smaller buttons
                btn.setIconSize(QSize(28, 28))  # Slightly smaller icons
                
                # Update button style with increased transparency
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(43, 43, 43, 0.25);
                        border: none;
                        padding: 4px;
                        margin: 0px;
                        border-radius: 12px;
                    }
                    QPushButton:hover {
                        background-color: rgba(60, 60, 60, 0.35);
                    }
                    QPushButton:pressed {
                        background-color: rgba(30, 30, 30, 0.45);
                    }
                """)
        
        # Re-add buttons in the correct order
        button_order = ['new', 'dashboard', 'management', 'profile', 'pin', 'layout', 'opacity', 'close']
        print("\nDEBUG: Enforcing button order")
        print(f"DEBUG: Available buttons: {list(self.buttons.keys())}")
        
        # Check if management button should be included
        parent = self.parent()
        if parent and parent.current_user and parent.current_user.role.lower() in ["admin", "manager"]:
            print("DEBUG: User has admin/manager role, management button should be present")
        else:
            print("DEBUG: User does not have admin/manager role, management button should not be present")
            if "management" in button_order:
                button_order.remove("management")
        
        # Add buttons in order
        for btn_id in button_order:
            if btn_id in self.buttons:
                print(f"DEBUG: Adding button {btn_id} to layout")
                new_layout.addWidget(self.buttons[btn_id], 0, Qt.AlignCenter)
            else:
                print(f"DEBUG: Button {btn_id} not found in buttons dictionary")
        
        # Set the new layout
        QWidget().setLayout(self.container.layout())
        self.container.setLayout(new_layout)
        
        # Update window size and position
        self.load_position()
        
        # Force a repaint
        self.update()

    def update_window_flags(self):
        """Update window flags based on pin state"""
        try:
            # Store current position and visibility
            pos = self.pos()
            was_visible = self.isVisible()
            
            # Hide window before changing flags
            self.hide()
            
            # Set base flags
            flags = Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
            
            # Add WindowStaysOnTopHint if pinned
            if self.is_pinned:
                flags |= Qt.WindowStaysOnTopHint
            
            # Apply new flags
            self.setWindowFlags(flags)
            
            # Restore visibility and position
            if was_visible:
                self.show()
                self.raise_()
                self.move(pos)
                
        except Exception as e:
            print(f"Error updating window flags: {str(e)}")
            # Ensure window is shown even if there's an error
            self.show()
            self.raise_()
            
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        # Ensure minimum size based on orientation
        if self.is_vertical:
            if self.width() != 76:  # Fixed width for vertical layout
                self.setFixedWidth(76)
            if self.height() < 500:  # Minimum height for vertical layout
                self.setMinimumHeight(500)
        else:
            if self.width() < 800:  # Minimum width for horizontal layout
                self.setMinimumWidth(800)
            if self.height() != 80:  # Fixed height for horizontal layout
                self.setFixedHeight(80)

    def moveEvent(self, event):
        """Handle move events to keep window within available screen space and save position"""
        super().moveEvent(event)
        
        # Get the screen containing the center of the window
        center = self.geometry().center()
        screen = QApplication.screenAt(center)
        
        if screen:
            # Get available geometry for the current screen
            available_geometry = screen.availableGeometry()
            current_pos = self.pos()
            new_pos = current_pos
            
            # Keep window within screen bounds
            if current_pos.x() < available_geometry.left():
                new_pos.setX(available_geometry.left())
            elif current_pos.x() + self.width() > available_geometry.right():
                new_pos.setX(available_geometry.right() - self.width())
                
            if current_pos.y() < available_geometry.top():
                new_pos.setY(available_geometry.top())
            elif current_pos.y() + self.height() > available_geometry.bottom():
                new_pos.setY(available_geometry.bottom() - self.height())
                
            # Only move if position changed and not dragging
            if new_pos != current_pos and self.drag_position is None:
                self.move(new_pos)
            
            # Save position after manual move (when not dragging)
            if self.drag_position is None:
                self.save_position()

    def check_updates(self):
        """Check for new opportunities and notifications"""
        if not self.parent() or not self.parent().current_user:
            return
        
        try:
            # Use ZoneInfo for more robust timezone handling
            utc = ZoneInfo('UTC')
            current_time = datetime.now(utc)
            print(f"\nDEBUG: Checking updates at {current_time}")
            print(f"DEBUG: Last check time was {self.last_checked_time}")
            print(f"DEBUG: Last reminder time was {self.last_reminder_time}")
            
            # Add time difference debugging for 5-minute reminder
            try:
                time_since_reminder = (current_time - self.last_reminder_time).total_seconds()
                print(f"DEBUG: Seconds since last reminder: {time_since_reminder} (needs to be >300 for reminder)")
            except Exception as time_err:
                print(f"DEBUG: Error calculating time difference: {str(time_err)}")
                # If there's an error with the time calculation, reset the reminder time
                self.last_reminder_time = current_time
                time_since_reminder = 0
                print(f"DEBUG: Reset last_reminder_time to {current_time}")
        
            db = SessionLocal()
            
            # Make sure we use proper transaction management
            try:
                # Begin a new transaction
                db.begin()
                
                # Check for new opportunities
                try:
                    # SQL version - use case-insensitive matching
                    new_opportunities_query = text("""
                        SELECT id, title, display_title, description, status, created_at, creator_id
                        FROM opportunities 
                        WHERE LOWER(status) = 'new' 
                        AND creator_id != :user_id
                    """)
                    
                    result = db.execute(new_opportunities_query, {"user_id": str(self.parent().current_user.id)})
                    
                    # Process the raw SQL results into Opportunity objects safely
                    new_opportunities = []

                    valid_fields = ['id', 'title', 'display_title', 'description', 'status', 'created_at', 'creator_id', 'acceptor_id', 'completed_at', 'started_at', 'response_time', 'work_time', 'updated_at', 'systems', 'comments', 'files']
                    
                    for row in result:
                        try:
                            # Create Opportunity object - only pass expected fields
                            if hasattr(row, '_asdict'):
                                row_dict = row._asdict()
                            elif hasattr(row, '_mapping'):
                                # For SQLAlchemy 1.4+
                                row_dict = dict(row._mapping)
                            else:
                                # Fallback - direct dict conversion
                                row_dict = dict(row)
                                
                            # Filter row_dict to only include valid fields
                            filtered_dict = {k: v for k, v in row_dict.items() if k in valid_fields}
                            
                            # Create Opportunity object with filtered dict
                            opp = Opportunity(**filtered_dict)
                            new_opportunities.append(opp)
                        except Exception as row_err:
                            print(f"Error processing row: {str(row_err)}")
                            continue
                except Exception as sql_err:
                    print(f"Error with SQL approach: {str(sql_err)}")
                    db.rollback()  # Rollback on SQL error before trying ORM
                    db.begin()     # Start a fresh transaction
                    
                    # Fallback to ORM approach with case insensitive filter
                    try:
                        new_opportunities = db.query(Opportunity).filter(
                            Opportunity.status.ilike("new"),
                            Opportunity.creator_id != str(self.parent().current_user.id)
                        ).all()
                    except Exception as orm_err:
                        print(f"Error with ORM fallback: {str(orm_err)}")
                        db.rollback()  # Rollback transaction on failure
                        new_opportunities = []  # Set empty list to avoid errors
                
                # Debug logging for better troubleshooting
                print(f"DEBUG: New opportunities found in DB: {len(new_opportunities)}")
                for i, opp in enumerate(new_opportunities, 1):
                    print(f"  {i}. ID: {opp.id}, Title: {opp.title}, Status: {opp.status}, Creator: {opp.creator_id}")
                
                # Get all opportunity IDs for cleaning up viewed_opportunities
                all_new_opps_ids = {opp.id for opp in new_opportunities}
                print(f"DEBUG: All new opportunity IDs: {all_new_opps_ids}")
                
                # Debug before cleaning viewed opportunities set
                print(f"DEBUG: Viewed opportunities before cleanup: {self.viewed_opportunities}")
                self.viewed_opportunities = {opp_id for opp_id in self.viewed_opportunities if opp_id in all_new_opps_ids}
                print(f"DEBUG: Viewed opportunities after cleanup: {self.viewed_opportunities}")
                
                # Get opportunities that haven't been viewed
                unviewed_opportunities = [opp for opp in new_opportunities if opp.id not in self.viewed_opportunities]
                print(f"DEBUG: Found {len(unviewed_opportunities)} unviewed NEW opportunities")
                print(f"DEBUG: Total viewed opportunities: {len(self.viewed_opportunities)}")
                print(f"DEBUG: Total new opportunities: {len(new_opportunities)}")
                
                # Check new notifications (these are already filtered by user_id)
                try:
                    new_notifications = db.query(Notification).filter(
                        Notification.user_id == str(self.parent().current_user.id),
                        Notification.read == False
                    ).all()
                    
                    print(f"DEBUG: Found {len(new_notifications)} new notifications")
                except Exception as notif_err:
                    print(f"Error getting notifications: {str(notif_err)}")
                    db.rollback()  # Rollback transaction on failure
                    db.begin()     # Start a fresh transaction
                    new_notifications = []  # Set empty list to avoid errors
                
                # Update total notification count (unviewed opportunities + unread notifications)
                total_count = len(unviewed_opportunities) + len(new_notifications)
                print(f"DEBUG: Total notification count: {total_count}")
                
                # Only update notification count if it's different
                if total_count != self.notification_count:
                    self.notification_count = total_count
                    self.update_notification_badge()
                
                # Show notifications for new opportunities since last check
                for opp in new_opportunities:
                    if opp.id not in self.viewed_opportunities and opp.created_at > self.last_checked_time:
                        # Show detailed notification for this new opportunity
                        print(f"DEBUG: Sending notification for new opportunity: {opp.id} - {opp.title}")
                        self.show_windows_notification(
                            "New SI Opportunity",
                            f"Ticket: {opp.title}\nVehicle: {opp.display_title}\nDescription: {opp.description[:100]}..."
                        )
                        # Mark as viewed to prevent duplicate notifications
                        self.viewed_opportunities.add(opp.id)
                        print(f"DEBUG: Marked opportunity as viewed: {opp.id}")
                
                # Commit the transaction after all processing is complete
                db.commit()
                
                # Show periodic reminder of total unviewed opportunities (every 5 minutes)
                try:
                    current_seconds_since_reminder = (current_time - self.last_reminder_time).total_seconds()
                    reminder_condition = total_count > 0 and current_seconds_since_reminder > 300
                    print(f"DEBUG: Reminder condition: {reminder_condition} (total_count={total_count}, seconds_since_reminder={current_seconds_since_reminder})")
                    if reminder_condition:
                        print(f"DEBUG: Showing 5-minute reminder notification for {total_count} unviewed items")
                        self.show_windows_notification(
                            "Reminder",
                            f"You have {total_count} unviewed items requiring attention"
                        )
                        self.last_reminder_time = current_time
                        print(f"DEBUG: Updated last_reminder_time to {current_time}")
                except Exception as reminder_err:
                    print(f"DEBUG: Error in reminder logic: {str(reminder_err)}")
                    print(traceback.format_exc())
                
                # Show notifications for other notification types
                if len(new_notifications) > 0:
                    for notif in new_notifications:
                        if notif.id not in self.viewed_notifications:
                            self.show_windows_notification(
                                "New Notification",
                                notif.message
                            )
                            self.viewed_notifications.add(notif.id)
                
                # Update last check time only for future notifications
                self.last_checked_time = current_time
                
            except Exception as db_err:
                print(f"Database error in check_updates: {str(db_err)}")
                traceback.print_exc()
                # Always ensure we rollback on error
                try:
                    db.rollback()
                except:
                    pass
            finally:
                db.close()
        except Exception as outer_e:
            print(f"Critical error in check_updates: {str(outer_e)}")
            print(traceback.format_exc())

    def show_windows_notification(self, title, message):
        """Show in-app notification"""
        try:
            print(f"\nDEBUG: Creating notification - Title: {title}")
            print(f"DEBUG: Message content: {message[:50]}{'...' if len(message) > 50 else ''}")
            
            # Get absolute path to app icon for notification
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'resources', 'SI Opportunity Manager LOGO.png.png')
            if not os.path.exists(icon_path):
                icon_path = None
                print("DEBUG: Using default icon (icon path not found)")
            else:
                print(f"DEBUG: Found icon at {icon_path}")
            
            # Make sure notification_clicked method exists
            if not hasattr(self, 'notification_clicked') or not callable(self.notification_clicked):
                print("DEBUG: Warning - notification_clicked method not available or not callable")
            else:
                print("DEBUG: notification_clicked method is available")
            
            # Use the notification manager to show the notification
            print("DEBUG: Calling notification_manager.show_notification")
            notification = notification_manager.show_notification(
                title,
                message,
                icon_path=icon_path,
                duration=5,
                callback=self.notification_clicked
            )
            
            print(f"DEBUG: Notification created and displayed - ID: {id(notification)}")
            return notification
        except Exception as e:
            print(f"Error showing notification: {str(e)}")
            traceback.print_exc()
            return None
            
    def notification_clicked(self):
        """Handle notification click - open dashboard"""
        try:
            print("DEBUG: Notification clicked, opening dashboard")
            
            # First check if parent exists and has current_user
            if not self.parent():
                print("DEBUG: No parent found for toolbar")
                return
                
            if not self.parent().current_user:
                print("DEBUG: No current user found, cannot open dashboard")
                return
                
            # Get reference to parent's show_dashboard method
            show_dashboard_method = getattr(self.parent(), 'show_dashboard', None)
            if not show_dashboard_method or not callable(show_dashboard_method):
                print("DEBUG: Parent does not have a valid show_dashboard method")
                return
                
            # Use QTimer to ensure this runs in the main thread with proper delay
            QTimer.singleShot(100, lambda: self.parent().show_dashboard())
            
            # Clear notifications when dashboard is shown
            QTimer.singleShot(200, lambda: self.clear_notifications() if hasattr(self, 'clear_notifications') else None)
            
            print("DEBUG: Successfully triggered dashboard display")
        except Exception as e:
            print(f"Error handling notification click: {str(e)}")
            traceback.print_exc()

    def update_notification_badge(self):
        """Update the notification badge on the dashboard button"""
        try:
            print(f"DEBUG: Updating notification badge. Count: {self.notification_count}")
            if self.notification_count > 0:
                # Set the text and ensure it's visible
                self.dashboard_badge.setText(str(self.notification_count))
                self.dashboard_badge.show()
                
                # Position in top-right corner of the button
                button_rect = self.buttons["dashboard"].geometry()
                self.dashboard_badge.move(button_rect.right() - 15, button_rect.top() - 5)
                self.dashboard_badge.raise_()
                print("DEBUG: Showing notification badge")
            else:
                self.dashboard_badge.hide()
                print("DEBUG: Hiding notification badge")
        except Exception as e:
            print(f"Error updating notification badge: {str(e)}")
        
    def toggle_pin(self):
        """Toggle pin state and update window flags"""
        # Update pin state
        self.is_pinned = not self.is_pinned
        
        # Update pin button appearance with blue highlight when pinned
        if hasattr(self, 'pin_button'):
            if self.is_pinned:
                self.pin_button.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(25, 118, 210, 0.6);
                        color: white;
                        border: none;
                        padding: 4px;
                        border-radius: 12px;
                        font-size: 10px;
                        text-align: center;
                    }
                    QPushButton:hover {
                        background-color: rgba(30, 136, 229, 0.7);
                    }
                    QPushButton:pressed {
                        background-color: rgba(21, 101, 192, 0.8);
                    }
                """)
            else:
                # Reset to default dark style when unpinned
                self.pin_button.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(43, 43, 43, 0.25);
                        color: white;
                        border: none;
                        padding: 4px;
                        border-radius: 12px;
                        font-size: 10px;
                        text-align: center;
                    }
                    QPushButton:hover {
                        background-color: rgba(60, 60, 60, 0.35);
                    }
                    QPushButton:pressed {
                        background-color: rgba(30, 30, 30, 0.45);
                    }
                """)
        
        # Update window flags and ensure visibility
        self.update_window_flags()
        QApplication.processEvents()  # Process pending events
        self.show()
        self.raise_()
        
    def show_opacity_slider(self):
        """Show a popup with opacity slider control"""
        popup = QDialog(self)
        popup.setWindowTitle("Adjust Opacity")
        popup.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        
        # Create layout
        layout = QVBoxLayout(popup)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Add title label
        title = QLabel("Adjust Toolbar Opacity")
        title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Create slider
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(20)
        slider.setMaximum(100)
        slider.setValue(int(self.windowOpacity() * 100))
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3d3d3d;
                height: 8px;
                background: #2b2b2b;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1976D2;
                border: none;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1E88E5;
            }
        """)
        
        # Create value label
        value_label = QLabel(f"{slider.value()}%")
        value_label.setStyleSheet("color: white; font-size: 12px;")
        value_label.setAlignment(Qt.AlignCenter)
        
        # Update opacity when slider moves
        def update_opacity(value):
            self.setWindowOpacity(value / 100)
            value_label.setText(f"{value}%")
        
        slider.valueChanged.connect(update_opacity)
        
        # Add widgets to layout
        layout.addWidget(slider)
        layout.addWidget(value_label)
        
        # Add close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        close_btn.clicked.connect(popup.close)
        layout.addWidget(close_btn)
        
        # Style popup
        popup.setStyleSheet("""
            QDialog {
                background-color: rgba(43, 43, 43, 0.98);
                border: 1px solid #3d3d3d;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3d3d3d;
                height: 8px;
                background: #2b2b2b;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1976D2;
                border: none;
                width: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1E88E5;
            }
        """)
        
        # Set size and position
        popup.setFixedSize(300, 150)
        popup.move(
            self.mapToGlobal(QPoint(0, 0)).x() + (self.width() - popup.width()) // 2,
            self.mapToGlobal(QPoint(0, self.height())).y()
        )
        
        popup.exec_()
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_pinned:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_position is not None and not self.is_pinned:
            new_pos = event.globalPos() - self.drag_position
            self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def update_icon_colors(self):
        """Update the colors of the icons in a rainbow pattern"""
        try:
            self.current_hue = (self.current_hue + 0.005) % 1.0  # Slowly increment hue
            
            # Convert HSV to RGB (hue cycles, full saturation and value)
            color = QColor.fromHsvF(self.current_hue, 0.7, 1.0)
            
            # Update each button's icon color
            for btn_id, btn in self.buttons.items():
                # Skip buttons with static colors
                if btn_id in self.static_colors:
                    continue
                    
                # Get the current icon
                icon = btn.icon()
                if not icon.isNull():
                    pixmap = icon.pixmap(24, 24)
                    if not pixmap.isNull():
                        try:
                            # Convert to image for color manipulation
                            image = pixmap.toImage()
                            
                            # Apply new color while preserving alpha
                            for x in range(image.width()):
                                for y in range(image.height()):
                                    try:
                                        pixel_color = image.pixelColor(x, y)
                                        if pixel_color.alpha() > 0:
                                            new_color = QColor(color)
                                            new_color.setAlpha(pixel_color.alpha())
                                            image.setPixelColor(x, y, new_color)
                                    except Exception as pixel_error:
                                        # Skip problematic pixels
                                        print(f"Pixel error at {x},{y}: {str(pixel_error)}")
                                        continue
                            
                            # Convert back to pixmap and update button
                            colored_pixmap = QPixmap.fromImage(image)
                            if not colored_pixmap.isNull():
                                btn.setIcon(QIcon(colored_pixmap))
                        except Exception as img_error:
                            print(f"Image processing error for button {btn_id}: {str(img_error)}")
            
            return 0  # Return success to Windows message handler
            
        except Exception as e:
            print(f"Error updating icon colors: {str(e)}\nTraceback: {traceback.format_exc()}")
            return 0  # Return success even on error to prevent Windows message handler issues

    def closeEvent(self, event):
        """Stop the color timer when closing"""
        self.color_timer.stop()
        super().closeEvent(event)

    def apply_static_theme(self):
        """Apply a static color theme to all icons"""
        try:
            theme_colors = {
                "White Icons": "#FFFFFF",
                "Blue Theme": "#2196F3",
                "Green Theme": "#4CAF50",
                "Purple Theme": "#9C27B0"
            }
            
            print(f"Applying static theme: {self.current_theme}")
            
            # Ensure we have a valid theme
            if not hasattr(self, 'current_theme') or not self.current_theme or self.current_theme not in theme_colors:
                print(f"Warning: Unknown or empty theme: '{getattr(self, 'current_theme', None)}', defaulting to White Icons")
                self.current_theme = "White Icons"
            
            # Get the color for the theme
            color = QColor(theme_colors[self.current_theme])
            print(f"Using color: {color.name()} for theme: {self.current_theme}")
            
            # Update each button's icon color
            if not hasattr(self, 'buttons') or not self.buttons:
                print("Warning: No buttons found to update")
                return
            
            for btn_id, btn in self.buttons.items():
                # Skip buttons with static colors
                if hasattr(self, 'static_colors') and btn_id in self.static_colors:
                    print(f"Skipping static color button: {btn_id}")
                    continue
                
                try:
                    # Get the current icon
                    icon = btn.icon()
                    if not icon or icon.isNull():
                        print(f"Warning: Null icon for button {btn_id}")
                        continue
                    
                    pixmap = icon.pixmap(24, 24)
                    if not pixmap or pixmap.isNull():
                        print(f"Warning: Null pixmap for button {btn_id}")
                        continue
                
                    # Convert to image for color manipulation
                    image = pixmap.toImage()
                    if image.isNull():
                        print(f"Warning: Failed to convert pixmap to image for button {btn_id}")
                        continue
                
                    # Apply new color while preserving alpha
                    width = image.width()
                    height = image.height()
                
                    for x in range(width):
                        for y in range(height):
                            try:
                                pixel_color = image.pixelColor(x, y)
                                alpha = pixel_color.alpha()
                                if alpha > 0:
                                    new_color = QColor(color)
                                    new_color.setAlpha(alpha)
                                    image.setPixelColor(x, y, new_color)
                            except Exception as pixel_error:
                                # Skip problematic pixels
                                print(f"Pixel error at {x},{y}: {str(pixel_error)}")
                                continue
                
                    # Convert back to pixmap and update button
                    colored_pixmap = QPixmap.fromImage(image)
                    if not colored_pixmap.isNull():
                        btn.setIcon(QIcon(colored_pixmap))
                    else:
                        print(f"Warning: Failed to create colored pixmap for button {btn_id}")
                except Exception as e:
                    print(f"Error processing button {btn_id}: {str(e)}")
                    continue
                
            return True
        except Exception as e:
            print(f"Error applying static theme: {str(e)}")
            return False

    def update_theme(self, new_theme):
        """Update the toolbar's theme"""
        try:
            print(f"Updating theme to: {new_theme}")
            
            # Validate the theme
            valid_themes = ["Rainbow Animation", "White Icons", "Blue Theme", "Green Theme", "Purple Theme"]
            if not new_theme or new_theme not in valid_themes:
                print(f"Warning: Invalid theme '{new_theme}', defaulting to 'White Icons'")
                new_theme = "White Icons"
            
            # Stop color timer if it's running
            if hasattr(self, 'color_timer') and self.color_timer.isActive():
                self.color_timer.stop()
                print("Stopped color timer")
            
            # Update the current theme
            self.current_theme = new_theme
            print(f"Current theme set to: {self.current_theme}")
            
            # Save the theme preference to settings
            self.settings.setValue('icon_theme', new_theme)
            print(f"Saved theme preference to settings: {new_theme}")
            
            # Apply the appropriate theme
            if new_theme == "Rainbow Animation":
                # Start the color timer for rainbow animation
                print("Starting rainbow animation timer")
                if hasattr(self, 'color_timer'):
                    self.color_timer.start(50)  # Update every 50ms
            else:
                # Apply a static theme
                print(f"Applying user's saved theme: {new_theme}")
                self.apply_static_theme()
            
            return True
        except Exception as e:
            print(f"Error updating theme: {str(e)}")
            return False

    def clear_notifications(self):
        """Clear notifications without resetting viewed items"""
        try:
            # Get all unread notifications
            db = SessionLocal()
            try:
                # Begin transaction
                db.begin()
                
                # Use case-insensitive SQL query for new opportunities
                try:
                    new_opps_query = text("""
                        SELECT id, title, display_title, description, status, created_at, creator_id
                        FROM opportunities
                        WHERE LOWER(status) = 'new'
                        AND creator_id != :user_id
                    """)
                    
                    result = db.execute(new_opps_query, {"user_id": str(self.parent().current_user.id)})
                    
                    # Process the raw SQL results into Opportunity objects safely
                    new_opps = []

                    valid_fields = ['id', 'title', 'display_title', 'description', 'status', 'created_at', 'creator_id', 'acceptor_id', 'completed_at', 'started_at', 'response_time', 'work_time', 'updated_at', 'systems', 'comments', 'files']
                    
                    for row in result:
                        try:
                            # Create Opportunity object - only pass expected fields
                            if hasattr(row, '_asdict'):
                                row_dict = row._asdict()
                            elif hasattr(row, '_mapping'):
                                # For SQLAlchemy 1.4+
                                row_dict = dict(row._mapping)
                            else:
                                # Fallback - direct dict conversion
                                row_dict = dict(row)
                                
                            # Filter row_dict to only include valid fields
                            filtered_dict = {k: v for k, v in row_dict.items() if k in valid_fields}
                            
                            # Create Opportunity object with filtered dict
                            opp = Opportunity(**filtered_dict)
                            new_opps.append(opp)
                        except Exception as row_err:
                            print(f"Error processing row: {str(row_err)}")
                            continue
                except Exception as sql_err:
                    print(f"Error with SQL approach: {str(sql_err)}")
                    db.rollback()  # Rollback on error
                    db.begin()     # Start fresh transaction
                    
                    # Fallback to ORM approach with case insensitive filter
                    try:
                        new_opps = db.query(Opportunity).filter(
                            Opportunity.status.ilike("new"),
                            Opportunity.creator_id != str(self.parent().current_user.id)
                        ).all()
                    except Exception as orm_err:
                        print(f"Error with ORM fallback: {str(orm_err)}")
                        db.rollback()  # Rollback on failure
                        new_opps = []  # Use empty list to avoid errors
                
                # Only add to viewed_opportunities when dashboard is explicitly opened
                # This ensures we mark all current NEW opportunities as viewed
                print(f"DEBUG: Adding {len(new_opps)} new opportunities to viewed list")
                for opp in new_opps:
                    self.viewed_opportunities.add(opp.id)
                    print(f"DEBUG: Added opportunity to viewed list: {opp.id}")
                
                print(f"DEBUG: Cleared notifications - Marked {len(new_opps)} opportunities as viewed")
                print(f"DEBUG: Current viewed_opportunities size: {len(self.viewed_opportunities)}")
                
                # Reset notification count and hide badge
                self.notification_count = 0
                if hasattr(self, 'dashboard_badge'):
                    self.dashboard_badge.hide()
                
                # Clear viewed notifications set
                self.viewed_notifications.clear()
                
                # Commit all changes
                db.commit()
                
            except Exception as e:
                print(f"Error clearing notifications: {str(e)}")
                traceback.print_exc()
                # Ensure we rollback on error
                try:
                    db.rollback()
                except:
                    pass
            finally:
                db.close()
            
        except Exception as outer_e:
            print(f"Critical error clearing notifications: {str(outer_e)}")
            traceback.print_exc()

    def test_notification(self):
        """Send a test notification to diagnose notification system"""
        try:
            print("\nDEBUG: Sending test notification")
            self.show_windows_notification(
                "Test Notification", 
                "This is a test notification to verify the notification system is working properly."
            )
            print("DEBUG: Test notification sent")
            
            # Schedule a test reminder notification in 5 seconds
            QTimer.singleShot(5000, lambda: self.show_windows_notification(
                "Test Reminder", 
                "This is a test reminder notification sent 5 seconds after the first test."
            ))
            print("DEBUG: Scheduled test reminder for 5 seconds from now")
            
            # Also increase notification count and update badge
            self.notification_count += 1
            self.update_notification_badge()
            print(f"DEBUG: Updated notification badge count to {self.notification_count}")
            
            return True
        except Exception as e:
            print(f"Error sending test notification: {str(e)}")
            traceback.print_exc()
            return False

    def reset_all_notifications(self):
        """Force reset all notification tracking (for troubleshooting)"""
        try:
            # Clear all tracked opportunities
            self.viewed_opportunities.clear()
            self.viewed_notifications.clear()
            
            # Reset counts and badge
            self.notification_count = 0
            if hasattr(self, 'dashboard_badge'):
                self.dashboard_badge.hide()
                
            print("DEBUG: Completely reset all notification tracking")
            
            # Force immediate refresh of notifications
            self.check_updates()
            
            # Show confirmation using custom notification
            self.show_windows_notification(
                "Notifications Reset",
                "All notification tracking has been reset. You may see new notifications for previously viewed items."
            )
            
        except Exception as e:
            print(f"Error resetting notifications: {str(e)}")
            traceback.print_exc()

    def show_dashboard_menu(self, position):
        """Display context menu for dashboard button"""
        menu = QMenu()
        reset_action = menu.addAction("Reset Notifications")
        reset_action.triggered.connect(self.reset_all_notifications)
        
        # Position menu relative to the dashboard button
        button_pos = self.buttons["dashboard"].mapToGlobal(position)
        selected_action = menu.exec_(button_pos)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Set fixed size
        self.setFixedSize(300, 300)
            
        # Set window flags to ensure it stays on top and is frameless
        self.setWindowFlags(
            Qt.Window |  # Make it an independent window
            Qt.FramelessWindowHint |  # No window frame
            Qt.WindowStaysOnTopHint |  # Stay on top
            Qt.Tool  # Don't show in taskbar
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Add logo
        self.logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                'resources', 'SI Opportunity Manager LOGO.png.png')
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            scaled_pixmap = logo_pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
            self.logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo_label)
        
        # Add loading label
        self.loading_label = QLabel("Loading...")
        self.loading_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
            }
        """)
        self.loading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.loading_label)
        
        # Add stretch to center vertically
        layout.addStretch()
        
        # Set widget style
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
                border-radius: 15px;
            }
        """)
        
        # Center on screen
        self.center_on_screen()
        
    def center_on_screen(self):
        # Get the screen geometry
        screen = QApplication.primaryScreen().availableGeometry()
        # Calculate center position
        center_x = (screen.width() - self.width()) // 2
        center_y = (screen.height() - self.height()) // 2
        # Move to center
        self.move(screen.left() + center_x, screen.top() + center_y)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawRoundedRect(self.rect(), 15, 15)  # Added rounded corners

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Check dependencies before proceeding
        if not check_dependencies():
            QMessageBox.critical(
                self,
                "Dependency Error",
                "Required dependencies could not be installed. The application will now close."
            )
            sys.exit(1)
            
        self.current_user = None
        self.profile = None
        self.dashboard = None
        self.toolbar = None
        self.opportunity_form = None
        self.management_portal = None
        
        # Initialize auth widget
        self.auth = AuthWidget()
        self.auth.authenticated.connect(self.on_authentication)
        self.auth.create_account_requested.connect(self.show_account_creation)
        self.auth.show()
        
    def _process_asyncio_events(self):
        """Process asyncio events in the Qt event loop"""
        try:
            self.loop.stop()
            self.loop.run_forever()
        except Exception as e:
            print(f"Error processing asyncio events: {e}")
            
    def closeEvent(self, event):
        """Handle application close event"""
        try:
            # Hide all windows
            if hasattr(self, 'toolbar'):
                self.toolbar.hide()
            if hasattr(self, 'dashboard'):
                self.dashboard.hide()
            if hasattr(self, 'opportunity_form'):
                self.opportunity_form.hide()
            if hasattr(self, 'settings'):
                self.settings.hide()
            if hasattr(self, 'auth'):
                self.auth.hide()
            if hasattr(self, 'account_creation'):
                self.account_creation.hide()
            if hasattr(self, 'management_portal'):
                self.management_portal.hide()
                
            # Accept the close event
            event.accept()
        except Exception as e:
            print(f"Error during close: {str(e)}")
            event.accept()

    def on_authentication(self, user):
        """Handle successful authentication"""
        print(f"DEBUG: User authenticated - Role: {user.role}")
        self.current_user = user
        
        # Hide auth widget immediately
        self.auth.hide()
        
        # Create toolbar
        self.toolbar = FloatingToolbar(self)
        self.toolbar.show()
        
        # Create new dashboard with current user
        if hasattr(self, 'dashboard') and self.dashboard is not None:
            self.dashboard.deleteLater()
        self.dashboard = DashboardWidget(current_user=user)
        
        # Create management portal if user is admin/manager
        if user.role.lower() in ["admin", "manager"]:
            print("DEBUG: Creating management portal for admin/manager")
            self.management_portal = ManagementPortal(user, self)
            self.management_portal.refresh_needed.connect(self.on_management_refresh)
        
        # Initialize notification system
        db = SessionLocal()
        try:
            # Get last login time or use a default (24 hours ago)
            last_login = db.query(User.last_login).filter(User.id == user.id).scalar()
            if last_login:
                self.toolbar.last_checked_time = last_login
            else:
                # For new users or first login, check last 24 hours
                self.toolbar.last_checked_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Update last login time
            user_obj = db.query(User).filter(User.id == user.id).first()
            if user_obj:
                user_obj.last_login = datetime.now(timezone.utc)
                db.commit()
            
            # Get detailed statistics for ticket overview
            new_tickets = db.query(Opportunity).filter(
                Opportunity.status.ilike("new"),
                Opportunity.creator_id != str(user.id)
            ).count()
            
            completed_tickets = db.query(Opportunity).filter(
                Opportunity.status.ilike("completed")
            ).count()
            
            in_progress_tickets = db.query(Opportunity).filter(
                Opportunity.status.ilike("in progress")
            ).count()
            
            needs_info_tickets = db.query(Opportunity).filter(
                Opportunity.status.ilike("needs info")
            ).count()
            
            own_tickets = db.query(Opportunity).filter(
                Opportunity.creator_id == str(user.id)
            ).count()
            
            # Build statistics summary
            print(f"\nDEBUG: Dashboard Statistics:")
            print(f"New Tickets query found: {new_tickets}")
            print(f"In Progress Tickets: {in_progress_tickets}")
            print(f"Completed Tickets: {completed_tickets}")
            print(f"Needs Info Tickets: {needs_info_tickets}")
            print(f"User's Own Tickets: {own_tickets}")
            
            stats_summary = f"New Tickets: {new_tickets}\n"
            stats_summary += f"In Progress: {in_progress_tickets}\n"
            stats_summary += f"Completed: {completed_tickets}\n"
            stats_summary += f"Needs Info: {needs_info_tickets}\n"
            stats_summary += f"Your Tickets: {own_tickets}"
            
            # Use QTimer to slightly delay the notification to ensure proper initialization
            QTimer.singleShot(500, lambda: self.show_startup_notification(stats_summary))
            
            # Start notification check timer
            self.toolbar.check_updates()
            
            # Keep main window hidden but make it available for other components
            print("DEBUG: Authentication complete, main window remains hidden, toolbar visible")
            # self.show() - Don't show main window, just keep toolbar visible
            
        except Exception as e:
            print(f"Error initializing notifications: {e}")
            traceback.print_exc()
        finally:
            db.close()
            
    def show_startup_notification(self, stats_summary):
        """Show startup notification with reliable display"""
        try:
            print("DEBUG: Showing startup notification")
            
            # Get absolute path to app icon for notification
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                    'resources', 'SI Opportunity Manager LOGO.png.png')
            if not os.path.exists(icon_path):
                icon_path = None
                
            # Show custom notification with longer duration for startup
            notification_manager.show_notification(
                "SI Opportunity Manager - Dashboard Overview",
                stats_summary,
                icon_path=icon_path,
                duration=8,
                callback=self.toolbar.notification_clicked
            )
            
            # Also print to console as backup
            print(f"STARTUP NOTIFICATION:\nSI Opportunity Manager - Dashboard Overview\n{stats_summary}")
            
        except Exception as e:
            print(f"Error showing startup notification: {str(e)}")
            traceback.print_exc()

    def on_account_created(self, user):
        self.account_creation.hide()
        self.auth.show()

    def on_new_opportunity(self, opportunity):
        """Handle newly created opportunity"""
        if hasattr(self, 'toolbar'):
            # Update notification count
            self.toolbar.notification_count += 1
            self.toolbar.update_notification_badge()
            # Show notification
            self.toolbar.show_windows_notification(
                "New SI Opportunity",
                f"Ticket: {opportunity.title}\nVehicle: {opportunity.display_title}\nDescription: {opportunity.description[:100]}..."
            )

    def show_profile(self):
        """Show the user profile window"""
        if not self.profile:
            self.profile = ProfileWidget(self.current_user)
            self.profile.profile_updated.connect(self.on_profile_updated)
        self.profile.show()
        self.profile.activateWindow()

    def on_profile_updated(self):
        """Handle profile updates"""
        print("Profile update received")
        db = SessionLocal()
        try:
            # Refresh current user data
            print(f"Refreshing user data for ID: {self.current_user.id}")
            self.current_user = db.query(User).filter(User.id == self.current_user.id).first()
            print(f"User data refreshed, theme: {self.current_user.icon_theme}")
            
            # Update toolbar theme if it exists
            if hasattr(self, 'toolbar'):
                print("Updating toolbar theme")
                self.toolbar.update_theme(self.current_user.icon_theme)
            else:
                print("Warning: Toolbar not found")
            
            # Update other windows that might need refreshing
            if hasattr(self, 'dashboard'):
                print("Refreshing dashboard")
                self.dashboard.load_opportunities()
            if hasattr(self, 'management_portal') and self.management_portal is not None:
                try:
                    print("Refreshing management portal")
                    self.management_portal.load_data()
                except Exception as e:
                    print(f"Error updating management portal: {str(e)}\nTraceback: {traceback.format_exc()}")
        except Exception as e:
            print(f"Error in profile update: {str(e)}\nTraceback: {traceback.format_exc()}")
        finally:
            db.close()
            print("Profile update completed")

    def show_opportunity_form(self):
        # Create form if it doesn't exist
        if not self.opportunity_form:
            self.opportunity_form = OpportunityForm(str(self.current_user.id))
            # Connect the opportunity created signal to the toolbar
            self.opportunity_form.opportunity_created.connect(self.on_new_opportunity)
        self.opportunity_form.show()
        self.opportunity_form.raise_()
        self.opportunity_form.activateWindow()
        
    def show_dashboard(self):
        """Show and refresh dashboard"""
        if not self.current_user:
            QMessageBox.warning(self, "Error", "Please log in first")
            return
            
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()
        self.dashboard.load_opportunities()
        if hasattr(self, 'toolbar'):
            self.toolbar.clear_notifications()
        
    def show_account_creation(self):
        self.account_creation.show()
        self.account_creation.raise_()
        self.account_creation.activateWindow()
        
    def show_management_portal(self):
        """Show management portal for admins and managers"""
        if not self.current_user or self.current_user.role not in ["admin", "manager"]:
            QMessageBox.warning(self, "Access Denied", "You don't have permission to access the management portal.")
            return
            
        if not self.management_portal:
            self.management_portal = ManagementPortal(self.current_user, self)
            self.management_portal.refresh_needed.connect(self.on_management_refresh)
            
        self.management_portal.show()
        self.management_portal.raise_()
        self.management_portal.activateWindow()
        self.management_portal.load_data()
        
    def on_management_refresh(self):
        """Handle refresh requests from management portal"""
        if hasattr(self, 'dashboard'):
            self.dashboard.load_opportunities()
            
    def initUI(self):
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add logo at the top
        logo_label = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                'SI Opportunity Manager LOGO.png.png')
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(logo_label)
        
        # Create stacked widget for different pages
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Initialize windows (hidden initially)
        self.auth = AuthWidget()
        self.auth.authenticated.connect(self.on_authentication)
        self.auth.create_account_requested.connect(self.show_account_creation)
        
        self.account_creation = AccountCreationWidget()
        self.account_creation.account_created.connect(self.on_account_created)
        
        # Initialize dashboard with None user (will be set after authentication)
        self.dashboard = DashboardWidget()
        self.opportunity_form = None
        self.settings = SettingsWidget()
        self.profile = None
        self.management_portal = None
        
        # Show auth widget first
        self.auth.show()

def main():
    # Enable High DPI scaling before creating QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    # Create application
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application-wide stylesheet
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
        }
    """)
    
    # Create and show main window
    window = MainWindow()
    # window.show() - Don't show main window yet, it will be shown after authentication
    
    # Debug print all top-level windows
    print("\nDEBUG: Top-level windows at startup:")
    for widget in app.topLevelWidgets():
        print(f"DEBUG: Window: {widget.__class__.__name__}, Title: {widget.windowTitle()}, Visible: {widget.isVisible()}")
    
    # Show auth widget
    window.auth.show()
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 