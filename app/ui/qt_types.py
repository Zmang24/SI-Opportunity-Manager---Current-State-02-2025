from typing import TypeVar, Protocol
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtWidgets import QWidget

# Qt Alignment Constants
AlignCenter = Qt.AlignCenter
AlignLeft = Qt.AlignLeft
AlignRight = Qt.AlignRight
AlignTop = Qt.AlignTop
AlignBottom = Qt.AlignBottom

# Qt Window Flags
FramelessWindowHint = Qt.FramelessWindowHint
WindowStaysOnTopHint = Qt.WindowStaysOnTopHint
Tool = Qt.Tool
NoDropShadowWindowHint = Qt.NoDropShadowWindowHint

# Qt Mouse Buttons
LeftButton = Qt.LeftButton
RightButton = Qt.RightButton
MiddleButton = Qt.MiddleButton

# Qt Widget Attributes
WA_TranslucentBackground = Qt.WA_TranslucentBackground
WA_ShowWithoutActivating = Qt.WA_ShowWithoutActivating
WA_AlwaysShowToolTips = Qt.WA_AlwaysShowToolTips

# Qt Orientations
Horizontal = Qt.Horizontal
Vertical = Qt.Vertical

# Qt Transformations
SmoothTransformation = Qt.SmoothTransformation
KeepAspectRatio = Qt.KeepAspectRatio
IgnoreAspectRatio = Qt.IgnoreAspectRatio

# Qt Pen Styles
NoPen = Qt.NoPen

# Qt Window States
WindowMinimized = Qt.WindowMinimized

# Qt High DPI Settings
AA_EnableHighDpiScaling = Qt.AA_EnableHighDpiScaling
AA_UseHighDpiPixmaps = Qt.AA_UseHighDpiPixmaps
AA_UseStyleSheetPropagationInWidgetStyles = Qt.AA_UseStyleSheetPropagationInWidgetStyles
AA_DontCreateNativeWidgetSiblings = Qt.AA_DontCreateNativeWidgetSiblings

# Type definitions
QWidgetType = TypeVar('QWidgetType', bound=QWidget) 