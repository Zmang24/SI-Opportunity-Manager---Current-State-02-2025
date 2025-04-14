import os
from PyQt5.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QGraphicsOpacityEffect, QApplication)
from PyQt5.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtSignal, QEvent
from PyQt5.QtGui import QPixmap, QIcon, QColor, QPainter, QPainterPath, QFont

class CustomNotification(QWidget):
    """Custom in-app notification that mimics Windows toast notifications"""
    
    clicked = pyqtSignal()  # Signal emitted when notification is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint | 
            Qt.Tool |
            Qt.WA_ShowWithoutActivating
        )
        
        # Enable custom styling with transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Initialize UI
        self.initUI()
        
        # Track if user interacted with notification
        self.was_clicked = False
        
        # Animation properties
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)
        
        # Setup auto-close timer
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.start_fade_out)
        
        # Setup animation objects
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(300)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.InCubic)
        self.fade_out_animation.finished.connect(self.hide)
        
        # Connect close button
        self.close_button.clicked.connect(self.start_fade_out)
        
        # Install event filter to handle mouse clicks
        self.installEventFilter(self)
        
    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(8)
        
        # Header with title and close button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        # App icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(24, 24)
        
        # Title
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Close button
        self.close_button = QPushButton()
        self.close_button.setFixedSize(16, 16)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self.close_button.setText("✕")
        
        # Add widgets to header
        header_layout.addWidget(self.icon_label)
        header_layout.addWidget(self.title_label, 1)
        header_layout.addWidget(self.close_button)
        
        # Message content
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("""
            QLabel {
                color: #f0f0f0;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.3;
            }
        """)
        
        # Add layouts to main layout
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.message_label)
        
        # Set fixed size for the notification
        self.setFixedSize(320, 120)
    
    def set_content(self, title, message, icon_path=None):
        """Set the notification content"""
        # Set title and message
        self.title_label.setText(title)
        self.message_label.setText(message)
        
        # Set icon if provided
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            self.icon_label.setPixmap(pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            # Default icon if none provided
            self.icon_label.setText("ℹ️")
    
    def show_notification(self, duration=5):
        """Show the notification with fade-in animation and auto-close timer"""
        # Position notification at bottom-right corner of screen
        screen_geometry = QApplication.desktop().availableGeometry()
        x = screen_geometry.width() - self.width() - 20
        y = screen_geometry.height() - self.height() - 20
        self.move(x, y)
        
        # Show widget and start fade-in
        self.show()
        self.fade_in_animation.start()
        
        # Start the auto-close timer
        self.close_timer.start(duration * 1000)
    
    def start_fade_out(self):
        """Start the fade-out animation"""
        self.close_timer.stop()
        self.fade_out_animation.start()
    
    def eventFilter(self, obj, event):
        """Handle mouse events to detect clicks on the notification"""
        if obj == self:
            # Handle mouse press events
            if event.type() == QEvent.MouseButtonPress:
                print("DEBUG: Notification clicked")
                self.was_clicked = True
                
                # Emit the clicked signal
                self.clicked.emit()
                
                # Start fade out animation with a slight delay
                QTimer.singleShot(100, self.start_fade_out)
                
                # Return True to indicate we've handled the event
                return True
                
            # Also handle mouse release events as clicks for better user experience
            elif event.type() == QEvent.MouseButtonRelease:
                if not self.was_clicked:
                    print("DEBUG: Notification clicked (mouse release)")
                    self.was_clicked = True
                    self.clicked.emit()
                    QTimer.singleShot(100, self.start_fade_out)
                return True
        
        # Pass unhandled events to the parent class
        return super().eventFilter(obj, event)
    
    def paintEvent(self, event):
        """Custom paint event to create a rounded rectangle with shadow effect"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create rounded rectangle path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        
        # Set shadow by drawing a slightly larger black rounded rect first
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.drawRoundedRect(2, 2, self.width(), self.height(), 8, 8)
        
        # Draw main background with a dark semi-transparent color
        painter.fillPath(path, QColor(40, 40, 40, 230))
        
        # Draw a subtle border
        painter.setPen(QColor(60, 60, 60, 120))
        painter.drawPath(path)


class NotificationManager:
    """Manages the display of multiple notifications"""
    
    def __init__(self):
        self.active_notifications = []
        self.vertical_spacing = 10
    
    def show_notification(self, title, message, icon_path=None, duration=5, callback=None):
        """Show a notification and manage its position"""
        # Create new notification
        notification = CustomNotification()
        notification.set_content(title, message, icon_path)
        
        # Connect callback if provided
        if callback and callable(callback):
            print(f"DEBUG: Connecting callback to notification click")
            notification.clicked.connect(callback)
            # Store the callback reference to prevent garbage collection
            notification._callback_ref = callback
        
        # When a notification is closed, remove it from active list and reposition others
        notification.fade_out_animation.finished.connect(
            lambda: self.remove_notification(notification)
        )
        
        # Add to active notifications
        self.active_notifications.append(notification)
        
        # Position notification
        self.reposition_notifications()
        
        # Show notification
        notification.show_notification(duration)
        
        return notification
    
    def remove_notification(self, notification):
        """Remove a notification from the active list and reposition others"""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
            notification.deleteLater()
            self.reposition_notifications()
    
    def reposition_notifications(self):
        """Reposition all active notifications to stack from bottom up"""
        if not self.active_notifications:
            return
            
        screen_geometry = QApplication.desktop().availableGeometry()
        notification_width = self.active_notifications[0].width()
        notification_height = self.active_notifications[0].height()
        
        x = screen_geometry.width() - notification_width - 20
        y = screen_geometry.height() - notification_height - 20
        
        # Position notifications from bottom up
        for i, notification in enumerate(reversed(self.active_notifications)):
            notification_y = y - (notification_height + self.vertical_spacing) * i
            notification.move(x, notification_y)
    
    def clear_all(self):
        """Clear all active notifications"""
        for notification in self.active_notifications[:]:
            notification.start_fade_out()


# Create a global instance
notification_manager = NotificationManager() 