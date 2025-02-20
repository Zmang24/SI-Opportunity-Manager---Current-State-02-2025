import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QPushButton, QLabel, QStackedWidget, QSystemTrayIcon,
                           QMenu, QStyle, QHBoxLayout, QFrame, QSlider, QDialog, QMessageBox)
from PyQt5.QtCore import Qt, QSize, QPoint, QTimer, QSettings
from PyQt5.QtGui import QIcon, QPixmap, QImage, QTransform, QPainter, QColor, QLinearGradient
from app.ui.dashboard import DashboardWidget
from app.ui.opportunity_form import OpportunityForm
from app.ui.auth import AuthWidget
from app.ui.account_creation import AccountCreationWidget
from app.ui.settings import SettingsWidget
from app.ui.management_portal import ManagementPortal
from app.ui.profile import ProfileWidget
from app.database.connection import SessionLocal
from app.models.models import Opportunity, Notification, User
from datetime import datetime, timedelta, timezone
from win10toast import ToastNotifier

class NotificationBadge(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #ff4444;
                color: white;
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
                min-width: 20px;
                min-height: 20px;
            }
        """)
        self.hide()
        
        # Position the badge in the top-right corner of the parent
        if parent:
            self.setParent(parent)
            self.move(parent.width() - 25, 5)
            parent.resizeEvent = lambda e: self.updatePosition(e)
    
    def updatePosition(self, event):
        """Update badge position when parent is resized"""
        if self.parent():
            self.move(self.parent().width() - 25, 5)
    
    def setText(self, text):
        """Override setText to ensure proper sizing"""
        super().setText(text)
        self.adjustSize()
        if self.parent():
            self.updatePosition(None)
            
    def show(self):
        """Override show to ensure proper positioning"""
        super().show()
        if self.parent():
            self.updatePosition(None)

class DragHandle(QWidget):
    def __init__(self, parent=None, orientation=Qt.Horizontal):
        super().__init__(parent)
        self.orientation = orientation
        self.setMouseTracking(True)
        
        # Set fixed size based on orientation
        if orientation == Qt.Horizontal:
            self.setFixedSize(40, 10)
        else:
            self.setFixedSize(10, 40)
            
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
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw handle dots
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 100))
        
        if self.orientation == Qt.Horizontal:
            # Draw three horizontal dots
            for i in range(3):
                painter.drawEllipse(10 + (i * 10), 3, 4, 4)
        else:
            # Draw three vertical dots
            for i in range(3):
                painter.drawEllipse(3, 10 + (i * 10), 4, 4)

class PeekButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
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

    def toggle_state(self, is_expanded):
        self.setText("▶" if is_expanded else "◀")

class FloatingToolbar(QWidget):
    def __init__(self, parent=None):
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
        self.last_checked_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        self.viewed_opportunities = set()
        self.viewed_notifications = set()
        self.toaster = ToastNotifier()
        
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
        
        # Get user's color theme preference
        if self.parent() and self.parent().current_user:
            self.current_theme = self.parent().current_user.icon_theme
        else:
            self.current_theme = "Rainbow Animation"
            
        # Start color timer only if rainbow animation is selected
        if self.current_theme == "Rainbow Animation":
            self.color_timer.start(50)  # Update every 50ms for smooth animation
        else:
            self.apply_static_theme()

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
            # Skip management button if user is not admin/manager
            if btn_id == "management":
                parent = self.parent()
                if not parent or not parent.current_user:
                    continue
                if parent.current_user.role not in ["admin", "manager"]:
                    continue
                
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
            
            # Connect button signals
            if btn_id == "new":
                btn.clicked.connect(lambda: self.parent().show_opportunity_form() if self.parent() and self.parent().current_user else None)
            elif btn_id == "dashboard":
                btn.clicked.connect(lambda: self.parent().show_dashboard() if self.parent() and self.parent().current_user else None)
                self.dashboard_badge = NotificationBadge(btn)
                self.dashboard_badge.hide()
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
        for btn_id in button_order:
            if btn_id in self.buttons:
                new_layout.addWidget(self.buttons[btn_id], 0, Qt.AlignCenter)
        
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
        if not self.parent().current_user:
            return
            
        current_time = datetime.now(timezone.utc)
        print(f"\nDEBUG: Checking updates at {current_time}")
        print(f"DEBUG: Last check time was {self.last_checked_time}")
        
        db = SessionLocal()
        try:
            # Check new opportunities (notify about all new tickets)
            new_opportunities = db.query(Opportunity).filter(
                Opportunity.created_at > self.last_checked_time,
                Opportunity.creator_id != self.parent().current_user.id,  # Don't notify for own tickets
                Opportunity.status.ilike("New")  # Case-insensitive status check
            ).all()
            
            print(f"DEBUG: Found {len(new_opportunities)} new opportunities")
            
            # Check new notifications (these are already filtered by user_id)
            new_notifications = db.query(Notification).filter(
                Notification.user_id == self.parent().current_user.id,
                Notification.created_at > self.last_checked_time,
                Notification.read == False
            ).all()
            
            print(f"DEBUG: Found {len(new_notifications)} new notifications")
            
            # Get total unread notifications for badge count
            total_unread = db.query(Notification).filter(
                Notification.user_id == self.parent().current_user.id,
                Notification.read == False
            ).count()
            
            print(f"DEBUG: Total unread notifications: {total_unread}")
            
            # Handle new opportunities
            if new_opportunities:
                for opp in new_opportunities:
                    if opp.id not in self.viewed_opportunities:
                        print(f"DEBUG: Showing notification for new opportunity {opp.id}")
                        self.show_windows_notification(
                            "New SI Opportunity",
                            f"New Ticket Available!\nTitle: {opp.title}\nVehicle: {opp.display_title}\nDescription: {opp.description[:100]}..."
                        )
                        self.viewed_opportunities.add(opp.id)
            
            # Handle new notifications (these are already targeted to the user)
            if new_notifications:
                for notif in new_notifications:
                    if notif.id not in self.viewed_notifications:
                        print(f"DEBUG: Showing notification {notif.id} of type {notif.type}")
                        self.show_windows_notification(
                            "SI Opportunity Update",
                            notif.message
                        )
                        self.viewed_notifications.add(notif.id)
            
            # Update notification badge with total unread count
            print(f"DEBUG: Setting notification count to {total_unread}")
            self.notification_count = total_unread
            self.update_notification_badge()
                
            self.last_checked_time = current_time
            
        finally:
            db.close()
            
    def show_windows_notification(self, title, message):
        """Show Windows notification"""
        self.toaster.show_toast(
            title,
            message,
            duration=5,
            threaded=True
        )
        
    def update_notification_badge(self):
        """Update the notification badge on the dashboard button"""
        if self.notification_count > 0:
            self.dashboard_badge.setText(str(self.notification_count))
            self.dashboard_badge.show()
        else:
            self.dashboard_badge.hide()
            
    def clear_notifications(self):
        """Clear notification count and mark current items as viewed"""
        if not self.parent().current_user:
            return
            
        db = SessionLocal()
        try:
            # Mark all notifications as read
            notifications = db.query(Notification).filter(
                Notification.user_id == self.parent().current_user.id,
                Notification.read == False
            ).all()
            
            for notif in notifications:
                notif.read = True
                self.viewed_notifications.add(notif.id)
            
            # Get all opportunities for reference
            opportunities = db.query(Opportunity).all()
            self.viewed_opportunities.update(opp.id for opp in opportunities)
            
            db.commit()
            
            # Reset notification count
            self.notification_count = 0
            self.update_notification_badge()
            
            # Update last checked time to avoid re-notifying
            self.last_checked_time = datetime.now()
        finally:
            db.close()
        
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
                
                # Convert to image for color manipulation
                image = pixmap.toImage()
                
                # Apply new color while preserving alpha
                for x in range(image.width()):
                    for y in range(image.height()):
                        pixel_color = image.pixelColor(x, y)
                        if pixel_color.alpha() > 0:
                            new_color = QColor(color)
                            new_color.setAlpha(pixel_color.alpha())
                            image.setPixelColor(x, y, new_color)
                
                # Convert back to pixmap and update button
                colored_pixmap = QPixmap.fromImage(image)
                btn.setIcon(QIcon(colored_pixmap))

    def closeEvent(self, event):
        """Stop the color timer when closing"""
        self.color_timer.stop()
        super().closeEvent(event)

    def apply_static_theme(self):
        """Apply a static color theme to all icons"""
        theme_colors = {
            "White Icons": "#FFFFFF",
            "Blue Theme": "#2196F3",
            "Green Theme": "#4CAF50",
            "Purple Theme": "#9C27B0"
        }
        
        if self.current_theme in theme_colors:
            color = QColor(theme_colors[self.current_theme])
            
            # Update each button's icon color
            for btn_id, btn in self.buttons.items():
                # Skip buttons with static colors
                if btn_id in self.static_colors:
                    continue
                    
                # Get the current icon
                icon = btn.icon()
                if not icon.isNull():
                    pixmap = icon.pixmap(24, 24)
                    
                    # Convert to image for color manipulation
                    image = pixmap.toImage()
                    
                    # Apply new color while preserving alpha
                    for x in range(image.width()):
                        for y in range(image.height()):
                            pixel_color = image.pixelColor(x, y)
                            if pixel_color.alpha() > 0:
                                new_color = QColor(color)
                                new_color.setAlpha(pixel_color.alpha())
                                image.setPixelColor(x, y, new_color)
                    
                    # Convert back to pixmap and update button
                    colored_pixmap = QPixmap.fromImage(image)
                    btn.setIcon(QIcon(colored_pixmap))

    def update_theme(self, theme):
        """Update the color theme"""
        self.current_theme = theme
        
        # Stop color timer if not using rainbow animation
        if theme != "Rainbow Animation":
            self.color_timer.stop()
            self.apply_static_theme()
        else:
            # Start color timer for rainbow animation
            self.current_hue = 0.0
            self.color_timer.start(50)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Set the size to match the parent if provided
        if parent:
            self.setGeometry(parent.rect())
        else:
            self.setFixedSize(200, 200)
            
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
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
        
        # Set widget style
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 180);
            }
        """)
        
        # If no parent, center on screen
        if not parent:
            self.center_on_screen()
        
    def center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.width() // 2 - self.width() // 2,
            screen.height() // 2 - self.height() // 2
        )
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.drawRect(self.rect())

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('SI Opportunity Manager')
        
        # Load and set the window icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                'SI Opportunity Manager LOGO.png.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.current_user = None
        self.opportunity_form = None
        self.dashboard = None
        self.management_portal = None
        self.profile = None
        self.auth_widget = None
        self.account_creation = None
        self.initUI()
        
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
        
        # Create floating toolbar (but don't show it yet)
        self.toolbar = FloatingToolbar(self)
        
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
            
    def on_authentication(self, user):
        """Handle successful authentication"""
        print(f"DEBUG: User authenticated - Role: {user.role}")
        self.current_user = user
        
        # Hide auth widget immediately
        self.auth.hide()
        QApplication.processEvents()  # Force update to hide auth
        
        # Create and show loading overlay
        loading = LoadingOverlay()
        loading.show()
        loading.raise_()
        QApplication.processEvents()  # Force update to show loading
        
        # Recreate dashboard with current user
        if hasattr(self, 'dashboard'):
            self.dashboard.deleteLater()
        self.dashboard = DashboardWidget(current_user=user)
        
        # Create management portal if user is admin/manager
        if user.role in ["admin", "manager"]:
            print("DEBUG: Creating management portal for admin/manager")
            self.management_portal = ManagementPortal(user, self)
            self.management_portal.refresh_needed.connect(self.on_management_refresh)
        
        # Recreate toolbar to ensure proper button visibility
        if hasattr(self, 'toolbar'):
            self.toolbar.deleteLater()
        self.toolbar = FloatingToolbar(self)
        
        # Initialize last_checked_time to user's last login or 24 hours ago
        db = SessionLocal()
        try:
            last_login = db.query(User.last_login).filter(User.id == user.id).scalar()
            if last_login:
                self.toolbar.last_checked_time = last_login
            else:
                self.toolbar.last_checked_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            # Update last login time
            user_obj = db.query(User).filter(User.id == user.id).first()
            user_obj.last_login = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()
        
        def finish_loading():
            # Hide loading overlay
            loading.hide()
            loading.deleteLater()
            
            # Show toolbar
            self.toolbar.show()
            self.toolbar.raise_()
            self.toolbar.load_position()
        
        # Show loading for at least 500ms to ensure smooth transition
        QTimer.singleShot(500, finish_loading)
        
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
        db = SessionLocal()
        try:
            # Refresh current user data
            self.current_user = db.query(User).filter(User.id == self.current_user.id).first()
            
            # Update toolbar theme if it exists
            if hasattr(self, 'toolbar'):
                self.toolbar.update_theme(self.current_user.icon_theme)
            
            # Update other windows that might need refreshing
            if hasattr(self, 'dashboard'):
                self.dashboard.load_opportunities()
            if hasattr(self, 'management_portal') and self.management_portal is not None:
                try:
                    self.management_portal.load_data()
                except Exception as e:
                    print(f"Warning: Error updating management portal: {str(e)}")
        finally:
            db.close()

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
            
    def changeEvent(self, event):
        """Handle window state changes"""
        try:
            if event.type() == 105:  # WindowStateChange event type
                if self.windowState() & Qt.WindowMinimized:
                    # Minimize all windows
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
            super().changeEvent(event)
        except Exception as e:
            print(f"Error during window state change: {str(e)}")
            
    def moveEvent(self, event):
        """Handle window move events"""
        try:
            super().moveEvent(event)
        except Exception as e:
            print(f"Error during window move: {str(e)}")
            
    def resizeEvent(self, event):
        """Handle window resize events"""
        try:
            super().resizeEvent(event)
        except Exception as e:
            print(f"Error during window resize: {str(e)}")
            
    def event(self, event):
        """Handle all other window events"""
        try:
            return super().event(event)
        except Exception as e:
            print(f"Error handling window event: {str(e)}")
            return True  # Prevent event propagation on error

def main():
    # Enable High DPI scaling before creating QApplication
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Enable additional attributes after QApplication creation
    QApplication.setAttribute(Qt.AA_UseStyleSheetPropagationInWidgetStyles)
    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    
    # Set application-wide stylesheet with tooltip style
    app.setStyleSheet("""
        QToolTip { 
            background-color: rgba(43, 43, 43, 0.95);
            color: white;
            border: 1px solid #555555;
            padding: 5px;
            border-radius: 4px;
            font-size: 12px;
            margin: 0px;
        }
        QMainWindow {
            background-color: #1e1e1e;
        }
        QWidget {
            color: #ffffff;
            font-size: 12px;
        }
    """)
    
    window = MainWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 