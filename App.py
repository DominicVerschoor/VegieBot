import sys
import os
import re
import time
import json

# GUI imports
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, 
    QFrame, QHBoxLayout, QTextEdit, QCheckBox, QSizePolicy, QDialog
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, QObject, Signal, QSettings
from PySide6.QtGui import QFont, QIcon, QPixmap

# Optional dependencies
try:
    import pygame
    pygame.mixer.init()
    HAS_AUDIO = True
except ImportError:
    print("Warning: pygame not installed. Sound effects disabled.")
    HAS_AUDIO = False

try:
    import pyautogui
except ImportError:
    print("Warning: pyautogui not installed. Mouse commands disabled.")
    pyautogui = None

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    print("Warning: pyperclip not installed. Clipboard commands disabled.")
    pyperclip = None
    HAS_CLIPBOARD = False

# Local imports
from MonitorTracking import HeadMouseTracker
from VoiceControl import VoskMicRecognizer
from Chatbot import HaloChat

class DragButton(QPushButton):
    """Button that can be dragged when sidebar is collapsed"""
    def __init__(self, text, parent):
        super().__init__(text)
        self.parent = parent
        self.drag_start = None
        self.dragged = False
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start = event.globalPosition().toPoint()
            self.dragged = False
            if not self.parent.expanded:
                self.parent.mousePressEvent(event)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_start:
            current = event.globalPosition().toPoint()
            distance = (current - self.drag_start).manhattanLength()
            
            if distance > 5:
                self.dragged = True
            
            if not self.parent.expanded and self.dragged:
                self.parent.mouseMoveEvent(event)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.parent.expanded:
                self.parent.mouseReleaseEvent(event)
            
            self.drag_start = None
            
            if self.dragged:
                event.accept()
                self.dragged = False
                return
        
        super().mouseReleaseEvent(event)

class VoiceWindow(QWidget):
    """Floating window that displays voice typing feedback"""
    
    def __init__(self, sidebar=None):
        super().__init__()
        self.setWindowTitle("Voice Typing")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.sidebar = sidebar
        self.width = 400
        self.height = 200
        self.setFixedSize(self.width, self.height)
        
        self.setup_ui()
        self.position_window()
    
    def setup_ui(self):
        """Setup the voice window UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header
        self.header = QLabel("🎤 Voice Typing")
        self.header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.header.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background-color: rgba(52, 73, 94, 0.9);
                padding: 8px 15px;
                border-radius: 8px;
                border: 2px solid #3498db;
            }
        """)
        layout.addWidget(self.header)
        
        # Sentence display
        self.sentence = QLabel("")
        self.sentence.setWordWrap(True)
        self.sentence.setFont(QFont("Segoe UI", 18))
        self.sentence.setMinimumHeight(80)
        self.sentence.setStyleSheet("""
            QLabel {
                background-color: rgba(44, 62, 80, 0.95);
                color: #ecf0f1;
                padding: 15px;
                border-radius: 10px;
                border: 2px solid #2ecc71;
                font-size: 18px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.sentence)
        
        # Status
        self.status = QLabel("Say 'halo type' to start")
        self.status.setFont(QFont("Segoe UI", 12))
        self.status.setStyleSheet("""
            QLabel {
                color: #bdc3c7;
                background-color: rgba(52, 73, 94, 0.8);
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.status)
        
        # Set main window style
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 15px;
            }
        """)
    
    def update_sentence(self, text):
        """Update the sentence display"""
        self.sentence.setText(text)
    
    def update_status(self, text):
        """Update the status"""
        self.status.setText(text)
    
    def position_window(self):
        """Position window next to the sidebar"""
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - 420 - self.width - 30
        y = screen.height() - self.height - 30
        self.move(x, y)
    
    def show_typing_window(self):
        """Show the voice window"""
        self.position_window()
        self.show()
        self.raise_()
        self.activateWindow()
    
    def hide_typing_window(self):
        """Hide the voice window"""
        self.hide()
    

class VoiceController(QObject):
    """Handles voice command signals for thread-safe operation"""
    # Mouse signals
    left_click = Signal()
    right_click = Signal()
    middle_click = Signal()
    shift_click = Signal()
    double_click = Signal()
    scroll_up = Signal()
    scroll_down = Signal()
    
    # Voice typing signals
    start_typing = Signal()
    finish_typing = Signal()
    add_word = Signal(str)
    redo = Signal()
    back = Signal()
    insert = Signal()
    
    # AI chat signals
    start_ai_typing = Signal()
    finish_ai_typing = Signal()
    add_ai_word = Signal(str)
    
    # System signals
    update_chat_input = Signal(str)
    shutdown = Signal()
    
    def __init__(self):
        super().__init__()
        # Connect mouse signals
        self.left_click.connect(self.do_left_click)
        self.right_click.connect(self.do_right_click)
        self.middle_click.connect(self.do_middle_click)
        self.shift_click.connect(self.do_shift_click)
        self.double_click.connect(self.do_double_click)
        self.scroll_up.connect(self.do_scroll_up)
        self.scroll_down.connect(self.do_scroll_down)
        
        # Voice typing state
        self.voice_typing = False
        self.sentence = ""
        
        # AI chat state
        self.ai_typing = False
        self.ai_sentence = ""
    def do_left_click(self):
        if pyautogui:
            pyautogui.click()
    
    def do_right_click(self):
        if pyautogui:
            pyautogui.rightClick()
    
    def do_middle_click(self):
        if pyautogui:
            pyautogui.middleClick()
    
    def do_shift_click(self):
        if pyautogui:
            pyautogui.keyDown('shift')
            pyautogui.click()
            pyautogui.keyUp('shift')
    
    def do_double_click(self):
        if pyautogui:
            try:
                pyautogui.doubleClick()
                print("Double click performed")
            except Exception as e:
                print(f"Double click error: {e}")
    
    def do_scroll_up(self):
        if pyautogui:
            try:
                pyautogui.scroll(3)  # Positive value scrolls up
                print("Scroll up performed")
            except Exception as e:
                print(f"Scroll up error: {e}")
    
    def do_scroll_down(self):
        if pyautogui:
            try:
                pyautogui.scroll(-3)  # Negative value scrolls down
                print("Scroll down performed")
            except Exception as e:
                print(f"Scroll down error: {e}")

class HelpDialog(QDialog):
    """Help dialog showing available functions and voice commands"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HALO - Help & Available Functions")
        self.setWindowIcon(parent.windowIcon() if parent else QIcon())
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Dialog)
        
        # Settings for "don't remind me" checkbox
        self.settings = QSettings("HALO", "VegieBot")
        
        self.setup_ui()
        self.center_on_screen()
    
    def setup_ui(self):
        """Setup the help dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("🎯 HALO - Available Functions")
        header.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Content area
        content = QTextEdit()
        content.setReadOnly(True)
        content.setFont(QFont("Segoe UI", 11))
        content.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 2px solid #e1e8ed;
                border-radius: 10px;
                padding: 15px;
                font-size: 11px;
            }
        """)
        
        help_text = """
<h2 style="color: #e74c3c;">🎤 Voice Commands</h2>
<p><b>"halo type"</b> - Start voice typing mode</p>
<p><b>"halo help"</b> - Start AI chat typing mode</p>
<p><b>"halo back"</b> - Remove last word</p>
<p><b>"halo redo"</b> - Clear and restart sentence</p>
<p><b>"halo in"</b> - Insert text and continue</p>
<p><b>"halo done"</b> - Finish and type sentence/send to AI</p>
<p><b>"halo copy"</b> / <b>"halo coffee"</b> - Copy text after "Copy below:" from chatbot</p>
<p><b>"halo paste"</b> - Paste clipboard content (Ctrl+V)</p>
<p><b>"enter"</b> / <b>"halo enter"</b> - Press Enter key</p>
<p><b>"halo deactivate"</b> - Turn off all features</p>
<p><b>"halo close"</b> - Shutdown application</p>

<h2 style="color: #3498db;">🖱️ Mouse Commands</h2>
<p><b>"click"</b> / <b>"halo click"</b> - Left mouse click</p>
<p><b>"right click"</b> / <b>"halo right click"</b> - Right mouse click</p>
<p><b>"double click"</b> / <b>"halo double click"</b> - Double click</p>
<p><b>"shift click"</b> / <b>"halo shift click"</b> - Shift + left click</p>
<p><b>"scroll up"</b> / <b>"halo scroll up"</b> - Scroll up on page</p>
<p><b>"scroll down"</b> / <b>"halo scroll down"</b> - Scroll down on page</p>

<h2 style="color: #8800ff;">🤖 AI Features</h2>
<p><b>AI Agent</b> - Chat with HALO AI assistant</p>
<p><b>Voice-to-AI</b> - Use "halo help" to dictate questions directly to AI</p>
<p><b>Smart Responses</b> - Ask about anything: math, science, writing, etc.</p>

<h2 style="color: #ff0000;">👁️ Face Tracking</h2>
<p><b>Head Mouse</b> - Control mouse cursor with head movements</p>
<p><b>Performance Mode</b> - Toggle between power saving and fast mode</p>
<p><b>Hands-free Control</b> - Navigate without touching mouse</p>

<h2 style="color: #0066ff;">⚡ Quick Actions</h2>
<p><b>Activate All</b> - Turn on all features at once</p>
<p><b>Deactivate All</b> - Turn off all features at once</p>
<p><b>Toggle Sidebar</b> - Minimize to circular HALO icon</p>
<p><b>Always On Top</b> - Stay visible over other applications</p>
        """
        
        content.setHtml(help_text)
        layout.addWidget(content)
        
        # Bottom section with checkbox and buttons
        bottom_layout = QHBoxLayout()
        
        # Don't remind me checkbox
        self.dont_remind_checkbox = QCheckBox("Don't show this help on startup")
        self.dont_remind_checkbox.setFont(QFont("Segoe UI", 10))
        self.dont_remind_checkbox.setChecked(self.settings.value("dont_show_help", False, type=bool))
        bottom_layout.addWidget(self.dont_remind_checkbox)
        
        bottom_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Got it!")
        close_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        close_btn.setFixedSize(100, 40)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #0066FF;
                color: white;
                border: none;
                border-radius: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0044CC;
            }
        """)
        close_btn.clicked.connect(self.close_dialog)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def center_on_screen(self):
        """Center the dialog on the screen"""
        screen = QApplication.primaryScreen().availableGeometry()
        dialog_size = self.geometry()
        
        # Calculate center position
        x = (screen.width() - dialog_size.width()) // 2
        y = (screen.height() - dialog_size.height()) // 2
        
        self.move(x, y)
    
    def close_dialog(self):
        """Close dialog and save checkbox state"""
        self.settings.setValue("dont_show_help", self.dont_remind_checkbox.isChecked())
        self.accept()

class HaloApp(QMainWindow):
    """Main HALO application window with collapsible sidebar"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HALO Control Panel")
        
        # Window dimensions
        self.width_expanded = 420
        self.width_collapsed = 80
        
        # Set window icon
        self.set_window_icon()
        
        # Screen setup
        screen = QApplication.primaryScreen().availableGeometry()
        self.top_margin = 50
        self.bottom_margin = 50
        self.height = screen.height() - self.top_margin - self.bottom_margin
        
        # Feature states
        self.states = {
            'face_tracking': False,
            'ai_agent': False,
            'voice': False,
            'performance_mode': False
        }
        
        # Feature colors - bold red, purple, blue
        self.colors = {
            'face_tracking': '#FF0000',      # Bold Red
            'ai_agent': '#8800FF',           # Bold Purple  
            'voice': '#0066FF',              # Bold Blue
            'performance_mode': '#FF6600'    # Bold Orange
        }
        
        # Window setup
        self.setFixedSize(self.width_expanded, self.height)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # Position window
        self.move(screen.width() - self.width_expanded, self.top_margin)
        
        # State
        self.expanded = True
        
        # Create UI
        self.setup_ui()
        self.load_stylesheet()
        self.start_chat()
        
        # Show help dialog on first startup (unless disabled)
        QTimer.singleShot(1000, self.maybe_show_startup_help)
        
        # Drag support
        self.drag_pos = None
    
    def set_window_icon(self):
        """Set window icon from logo file"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'imgs', 'logo.png')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Icon load error: {e}")
    
    def setup_ui(self):
        """Setup the main user interface"""
        # Clear any existing central widget first
        if self.centralWidget():
            old_widget = self.centralWidget()
            old_widget.setParent(None)
            old_widget.deleteLater()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toggle button - minimize/expand sidebar
        self.toggle_btn = DragButton("▶", self)
        self.toggle_btn.setObjectName("toggle_btn")
        self.toggle_btn.setFixedSize(35, 90)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        
        # Force the proper styling for the toggle button
        self.apply_toggle_button_style()
        
        # Content widget  
        self.content = QWidget()
        self.content.setFixedWidth(self.width_expanded - 35)
        
        content_layout = QVBoxLayout(self.content)
        content_layout.setSpacing(18)
        content_layout.setContentsMargins(25, 25, 25, 25)
        
        # Top section
        top_section = self.create_top_section()
        content_layout.addWidget(top_section)
        
        # Separator
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        content_layout.addWidget(separator)
        
        content_layout.addStretch()
        
        # Control buttons
        self.create_control_buttons(content_layout)
        
        content_layout.addStretch()
        
        # Chat interface
        self.chat_widget = self.create_chat_interface()
        self.chat_widget.setVisible(False)
        content_layout.addWidget(self.chat_widget)
        
        content_layout.addStretch()
        
        # Add to main layout - toggle button on left, content on right
        layout.addWidget(self.toggle_btn, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.content)
        
        # Voice window
        self.voice_window = VoiceWindow(self)
        
        # Voice controller
        self.voice_controller = VoiceController()
        self.connect_voice_signals()
    
    def create_top_section(self):
        """Create the top section with header and status"""
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(15, 15, 15, 8)
        
        header_layout = QHBoxLayout()
        
        # Title with logo
        title_container = self.create_title_section()
        header_layout.addWidget(title_container)
        header_layout.addStretch()
        
        # Help button
        help_btn = QPushButton("?")
        help_btn.setObjectName("help_btn")
        help_btn.setFixedSize(40, 40)
        help_btn.setFont(QFont("Segoe UI", 16, QFont.Bold))
        help_btn.setToolTip("Show help and available functions")
        help_btn.clicked.connect(self.show_help_dialog)
        header_layout.addWidget(help_btn)
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedSize(40, 40)
        close_btn.setFont(QFont("Segoe UI", 16, QFont.Bold))
        close_btn.clicked.connect(self.close_application)
        header_layout.addWidget(close_btn)
        
        # Status bar
        self.status = QLabel()
        self.status.setObjectName("status_label")
        self.status.setAlignment(Qt.AlignLeft)
        self.update_status()
        
        layout.addLayout(header_layout)
        layout.addWidget(self.status)
        
        return section
    
    def create_title_section(self):
        """Create title section with logo"""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Logo
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'imgs', 'logo.png')
            if os.path.exists(logo_path):
                logo = QLabel()
                pixmap = QPixmap(logo_path)
                scaled = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo.setPixmap(scaled)
                logo.setFixedSize(32, 32)
                layout.addWidget(logo)
        except Exception as e:
            print(f"Logo error: {e}")
        
        # Title
        title = QLabel(" HALO ")
        title.setObjectName("title_label")
        title.setAlignment(Qt.AlignLeft)
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        layout.addWidget(title)
        layout.addStretch()
        
        return container
    
    def create_control_buttons(self, layout):
        """Create control buttons section"""
        # Activate All button
        activate_all = QPushButton("⚡ Activate All")
        activate_all.setObjectName("activate_all_btn")
        activate_all.setMinimumHeight(70)
        activate_all.setFont(QFont("Segoe UI", 16, QFont.Bold))
        activate_all.clicked.connect(self.activate_all_toggles)
        layout.addWidget(activate_all)
        
        # Deactivate All button
        deactivate_all = QPushButton("🔴 Deactivate All")
        deactivate_all.setObjectName("deactivate_all_btn")
        deactivate_all.setMinimumHeight(70)
        deactivate_all.setFont(QFont("Segoe UI", 16, QFont.Bold))
        deactivate_all.clicked.connect(self.deactivate_all_toggles)
        layout.addWidget(deactivate_all)
        
        # Separator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)
        
        # Feature toggles
        self.face_btn = self.create_toggle("Face Tracking", 'face_tracking')
        layout.addWidget(self.face_btn)
        
        # Performance mode (hidden initially)
        self.perf_btn = self.create_toggle("⚡ Fast Mode", 'performance_mode')
        self.perf_btn.setVisible(False)
        layout.addWidget(self.perf_btn)
        
        self.ai_btn = self.create_toggle("AI Agent", 'ai_agent')
        layout.addWidget(self.ai_btn)
        
        self.voice_btn = self.create_toggle("Voice Detection", 'voice')
        layout.addWidget(self.voice_btn)
    
    def create_toggle(self, text, key):
        """Create a toggle switch button"""
        toggle = QCheckBox(text)
        toggle.setMinimumHeight(85)
        toggle.setFont(QFont("Segoe UI", 18, QFont.Bold))
        toggle.normal_color = self.colors[key]
        toggle.active_color = self.colors[key]
        toggle.state_key = key
        
        self.update_toggle_style(toggle)
        toggle.toggled.connect(lambda checked: self.on_toggle(toggle, checked))
        
        return toggle
    
    def connect_voice_signals(self):
        """Connect voice controller signals"""
        vc = self.voice_controller
        vc.update_chat_input.connect(self.update_chat_input_from_voice)
        vc.finish_typing.connect(self.finish_voice_typing)
        vc.start_typing.connect(self.start_voice_typing)
        vc.add_word.connect(self.add_to_sentence)
        vc.redo.connect(self.redo_sentence)
        vc.back.connect(self.remove_last_word)
        vc.insert.connect(self.insert_and_clear)
        vc.start_ai_typing.connect(self.start_ai_typing)
        vc.finish_ai_typing.connect(self.finish_ai_typing)
        vc.add_ai_word.connect(self.add_to_ai_sentence)
        vc.shutdown.connect(self.graceful_shutdown)
        
        
        
        
        
    
    
    def activate_all_toggles(self):
        """Activate all feature toggles"""
        toggles = [
            ('face_tracking', self.face_btn),
            ('ai_agent', self.ai_btn),
            ('voice', self.voice_btn)
        ]
        
        for key, btn in toggles:
            if not self.states.get(key, False):
                btn.setChecked(True)
        
        print("All features activated")

    def deactivate_all_toggles(self):
        """Deactivate all feature toggles"""
        toggles = [
            ('face_tracking', self.face_btn),
            ('ai_agent', self.ai_btn),
            ('voice', self.voice_btn),
            ('performance_mode', self.perf_btn)
        ]
        
        for key, btn in toggles:
            if self.states.get(key, False):
                btn.setChecked(False)
        
        print("All features deactivated")

    def copy_chatbot_text(self):
        """Copy text after 'Copy below:' from the chatbot response"""
        if not HAS_CLIPBOARD:
            print("Clipboard functionality not available - pyperclip not installed")
            return
        
        try:
            # Get all chat text
            chat_text = self.chat_display.toPlainText()
            
            if not chat_text.strip():
                print("No chat text available to copy")
                return
            
            # Look for "Copy below:" markers
            lines = chat_text.split('\n')
            copy_text = ""
            copying = False
            
            for line in lines:
                # Check if line contains "Copy below:" marker
                if "Copy below:" in line:
                    copying = True
                    continue
                
                # If we're in copy mode, collect text until we hit another marker or end
                if copying:
                    # Stop copying if we hit another "HALO:" response or "You:" message
                    if line.startswith("HALO:") or line.startswith("You:"):
                        break
                    
                    # Add the line to our copy text
                    if line.strip():  # Skip empty lines
                        if copy_text:
                            copy_text += "\n"
                        copy_text += line.strip()
            
            if copy_text:
                # Copy to clipboard
                pyperclip.copy(copy_text)
                print(f"Copied to clipboard: {copy_text[:50]}..." if len(copy_text) > 50 else f"Copied to clipboard: {copy_text}")
                
                # Play sound feedback
                self.play_beep_sound()
            else:
                print("No text found after 'Copy below:' markers")
                
        except Exception as e:
            print(f"Error copying chatbot text: {e}")

    def paste_clipboard_content(self):
        """Paste clipboard content using keyboard shortcut"""
        if not pyautogui:
            print("Paste functionality not available - pyautogui not installed")
            return
        
        try:
            # Use Ctrl+V to paste
            pyautogui.hotkey('ctrl', 'v')
            print("Paste command executed (Ctrl+V)")
            
            # Play sound feedback
            self.play_beep_sound()
            
        except Exception as e:
            print(f"Error pasting clipboard content: {e}")

    def press_enter_key(self):
        """Press Enter key using keyboard simulation"""
        if not pyautogui:
            print("Enter key functionality not available - pyautogui not installed")
            return
        
        try:
            # Press Enter key
            pyautogui.press('enter')
            print("Enter key pressed")
            
            # Play sound feedback
            self.play_beep_sound()
            
        except Exception as e:
            print(f"Error pressing Enter key: {e}")

    def graceful_shutdown(self):
        """Gracefully shut down operations one by one to prevent lag"""
        print("Initiating graceful shutdown...")
        
        # Step 1: Stop voice typing modes first
        if hasattr(self, 'voice_controller'):
            if self.voice_controller.voice_typing:
                self.stop_voice_typing()
                print("Voice typing stopped")
            if self.voice_controller.ai_typing:
                self.stop_ai_typing()
                print("AI typing stopped")
        
        # Step 2: Hide voice window
        if hasattr(self, 'voice_window'):
            self.voice_window.hide_typing_window()
            print("Voice window hidden")
        
        # Step 3: Stop voice recognition (force stop the recognizer thread)
        if hasattr(self, 'recognizer') and self.recognizer:
            try:
                self.recognizer.stop()
                self.recognizer = None
                print("Voice recognizer thread stopped")
            except Exception as e:
                print(f"Error stopping recognizer: {e}")
        
        # Also uncheck the voice button
        if self.states.get('voice', False):
            self.voice_btn.blockSignals(True)
            self.voice_btn.setChecked(False)
            self.states['voice'] = False
            self.voice_btn.blockSignals(False)
            print("Voice recognition stopped")
        
        # Step 4: Stop face tracking (force stop the tracker thread)
        if hasattr(self, 'tracker') and self.tracker:
            try:
                self.tracker.stop()
                self.tracker = None
                print("Face tracker thread stopped")
            except Exception as e:
                print(f"Error stopping tracker: {e}")
        
        # Also uncheck the face tracking button
        if self.states.get('face_tracking', False):
            self.face_btn.blockSignals(True)
            self.face_btn.setChecked(False)
            self.states['face_tracking'] = False
            self.face_btn.blockSignals(False)
            print("Face tracking stopped")
        
        # Step 5: Stop AI agent
        if self.states.get('ai_agent', False):
            self.ai_btn.blockSignals(True)
            self.ai_btn.setChecked(False)
            self.states['ai_agent'] = False
            self.ai_btn.blockSignals(False)
            print("AI agent stopped")
        
        # Step 6: Stop chat session
        if hasattr(self, 'chat') and self.chat:
            try:
                self.chat.stop()
                self.chat = None
                print("Chat session stopped")
            except Exception as e:
                print(f"Error stopping chat: {e}")
        
        # Step 7: Close any additional windows
        if hasattr(self, 'voice_window'):
            self.voice_window.close()
            print("Voice window closed")
        
        # Step 8: Force exit with more aggressive methods
        print("Forcing application exit...")
        self.force_exit()  # Direct call instead of using QTimer
        
    def force_exit(self):
        """Force exit the application using multiple methods"""
        print("Force exiting application...")
        
        try:
            # Try graceful Qt exit first
            QApplication.quit()
        except:
            pass
        
        try:
            # If Qt quit doesn't work, try sys.exit
            import sys
            sys.exit(0)
        except:
            pass
        
        try:
            # Last resort - force exit
            import os
            os._exit(0)
        except:
            pass
    
    def show_help_dialog(self):
        """Show the help dialog"""
        help_dialog = HelpDialog(self)
        help_dialog.exec()
    
    def maybe_show_startup_help(self):
        """Show help dialog on startup if not disabled"""
        settings = QSettings("HALO", "VegieBot")
        dont_show = settings.value("dont_show_help", False, type=bool)
        
        if not dont_show:
            self.show_help_dialog()
    
    def close_application(self):
        """Close the entire application"""
        print("Application closing...")
        QApplication.quit()

    def create_chat_interface(self):
        """Create the AI agent interface with assistant selection and feature cards"""
        chat_container = QWidget()
        chat_container.setObjectName("chat_container")
        # Remove fixed height to allow dynamic sizing
        chat_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(15, 10, 15, 10)  # Reduced margins
        chat_layout.setSpacing(12)  # Reduced spacing
        
        # HALO AI Header with logo
        ai_header_container = QWidget()
        ai_header_layout = QVBoxLayout(ai_header_container)
        ai_header_layout.setContentsMargins(0, 0, 0, 0)
        ai_header_layout.setSpacing(8)
        ai_header_layout.setAlignment(Qt.AlignCenter)
        
        # Try to add larger logo for AI interface
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'imgs', 'logo.png')
            if os.path.exists(logo_path):
                ai_logo_label = QLabel()
                pixmap = QPixmap(logo_path)
                scaled_pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                ai_logo_label.setPixmap(scaled_pixmap)
                ai_logo_label.setFixedSize(64, 64)
                ai_header_layout.addWidget(ai_logo_label, alignment=Qt.AlignCenter)
        except Exception as e:
            print(f"Could not load AI interface logo: {e}")
        
        halo_header = QLabel("HALO AI")
        halo_header.setObjectName("assistant_header")
        halo_header.setFont(QFont("Segoe UI", 28, QFont.Bold))
        halo_header.setAlignment(Qt.AlignCenter)
        ai_header_layout.addWidget(halo_header)
        
        ai_header_container.setMinimumHeight(80)  # Reduced from 120
        chat_layout.addWidget(ai_header_container)
        
        # Add smaller spacer
        chat_layout.addStretch(0)  # Remove stretch to save space
        
        # Suggested prompts
        prompts_widget = QWidget()
        prompts_layout = QVBoxLayout(prompts_widget)
        prompts_layout.setSpacing(12)
        
        email_prompt = QPushButton("📧 Write an email")
        email_prompt.setObjectName("prompt_btn")
        email_prompt.setMinimumHeight(75)
        email_prompt.setFont(QFont("Segoe UI", 18))
        email_prompt.clicked.connect(lambda: self.insert_prompt("Write an email"))
        
        photo_prompt = QPushButton("🌱 Explain how photosynthesis works")
        photo_prompt.setObjectName("prompt_btn")
        photo_prompt.setMinimumHeight(75)
        photo_prompt.setFont(QFont("Segoe UI", 18))
        photo_prompt.clicked.connect(lambda: self.insert_prompt("Explain how photosynthesis works"))
        
        prompts_layout.addWidget(email_prompt)
        prompts_layout.addWidget(photo_prompt)
        
        chat_layout.addWidget(prompts_widget)
        
        # Add smaller spacer
        chat_layout.addStretch(0)  # Remove stretch to save space
        
        # Chat input
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        # Text input - more compact
        self.chat_input = QTextEdit()
        self.chat_input.setObjectName("chat_input")
        self.chat_input.setPlaceholderText("Ask me anything...")
        self.chat_input.setMaximumHeight(120)  # Reduced from 180
        self.chat_input.setMinimumHeight(120)  # Reduced from 180
        self.chat_input.setFont(QFont("Segoe UI", 16))
        
        # Connect Enter key to send message
        def on_key_press(event):
            if event.key() == Qt.Key_Return and not event.modifiers():
                self.send_message()
            else:
                QTextEdit.keyPressEvent(self.chat_input, event)
        self.chat_input.keyPressEvent = on_key_press
        
        # Send button (arrow style) - match reduced input height
        send_btn = QPushButton("➤")
        send_btn.setObjectName("send_btn_arrow")
        send_btn.setFixedSize(100, 120)  # Reduced from 180 to match input
        send_btn.setFont(QFont("Segoe UI", 28))
        send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(send_btn)
        
        chat_layout.addWidget(input_container)
        
        # Chat display area - more compact
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chat_display")
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(150)  # Reduced from 200
        self.chat_display.setMinimumHeight(150)  # Reduced from 200
        self.chat_display.setFont(QFont("Segoe UI", 12))  # Smaller font
        self.chat_display.setPlaceholderText("AI responses will appear here...")
        self.chat_display.setVisible(False)  # Hidden initially
        chat_layout.addWidget(self.chat_display)
        
        # Voice button (keep for compatibility but hide)
        self.chat_voice_btn = QPushButton("🎤")
        self.chat_voice_btn.setObjectName("chat_voice_btn")
        self.chat_voice_btn.setFixedSize(70, 70)
        self.chat_voice_btn.setCheckable(True)
        self.chat_voice_btn.setToolTip("Voice input")
        self.chat_voice_btn.setVisible(False)  # Hidden in new design
        self.chat_voice_btn.toggled.connect(self.toggle_voice_input)
        self.chat_voice_btn.state_key = 'voice'
        
        return chat_container
    
    def insert_prompt(self, prompt_text):
        """Insert a prompt into the chat input"""
        self.chat_input.setPlainText(prompt_text)
        self.chat_input.setFocus()
    
    def toggle_voice_input(self, checked):
        """Toggle voice input recording based on button state"""
        if checked:
            # Start recording
            self.is_recording = True
            self.chat_input.setPlaceholderText("🎤 Listening... (Click mic again to stop)")
            self.chat_input.setObjectName("chat_input_recording")
            self.apply_stylesheet_to_widget(self.chat_input)
            print("Voice recording started...")
            
        else:
            # Stop recording
            self.is_recording = False
            self.chat_input.setPlaceholderText("Type your message here...")
            self.chat_input.setObjectName("chat_input_stopped")
            self.apply_stylesheet_to_widget(self.chat_input)
            
            print("Voice recording stopped. Transcribed text added to input.")

    def handle_voice_result(self, result_json: str):
        text = json.loads(result_json).get("text", "").strip().lower()
        print(f"Voice detected: '{text}'")  # Debug output
        
        # Process voice typing commands
        if self.process_voice_typing_command(text):
            return
        
        # Process mouse commands
        if self.process_voice_mouse_command(text):
            return
    
    def process_voice_mouse_command(self, text: str) -> bool:
        """Process voice commands for mouse actions. Returns True if command was processed."""
        if not pyautogui:
            return False
            
        # Define mouse command patterns with Qt signals (with and without halo prefix)
        mouse_commands = {
            # Click commands (with and without halo/hello/hey prefix)
            r'^click$': self.voice_controller.left_click,
            r'^left\s*click$': self.voice_controller.left_click,
            r'^(halo|hello|hey)\s+click$': self.voice_controller.left_click,
            r'^(halo|hello|hey)\s+left\s*click$': self.voice_controller.left_click,
            
            # Right click commands
            r'^right\s*click$': self.voice_controller.right_click,
            r'^(halo|hello|hey)\s+right\s*click$': self.voice_controller.right_click,
            
            # Middle click commands
            r'^middle\s*click$': self.voice_controller.middle_click,
            r'^middle\s*mouse$': self.voice_controller.middle_click,
            r'^(halo|hello|hey)\s+middle\s*click$': self.voice_controller.middle_click,
            r'^(halo|hello|hey)\s+middle\s*mouse$': self.voice_controller.middle_click,
            
            # Shift click commands
            r'^shift\s*\+\s*click$': self.voice_controller.shift_click,
            r'^shift\s*click$': self.voice_controller.shift_click,
            r'^(halo|hello|hey)\s+shift\s*click$': self.voice_controller.shift_click,
            
            # Double click commands
            r'^(double\s*click|doubleclick|double\s+tap)$': self.voice_controller.double_click,
            r'^(halo|hello|hey)\s+(double\s*click|doubleclick|double\s+tap)$': self.voice_controller.double_click,
            
            # Scroll commands
            r'^scroll\s*up$': self.voice_controller.scroll_up,
            r'^scroll\s*down$': self.voice_controller.scroll_down,
            r'^(halo|hello|hey)\s+scroll\s*up$': self.voice_controller.scroll_up,
            r'^(halo|hello|hey)\s+scroll\s*down$': self.voice_controller.scroll_down
        }
        
        # Check each pattern
        for pattern, signal in mouse_commands.items():
            if re.match(pattern, text):
                try:
                    print(f"Matched pattern '{pattern}' for text '{text}' - emitting signal")
                    signal.emit()
                    print(f"Executed mouse command: {text}")
                    return True
                except Exception as e:
                    print(f"Error executing mouse command '{text}': {e}")
                    return False
        
        print(f"No mouse command pattern matched for: '{text}'")
        return False
    
    def process_voice_typing_command(self, text: str) -> bool:
        """Process voice typing commands. Returns True if command was processed."""
        
        # Check for shutdown commands (highest priority)
        if self.matches_command(text, ["halo close", "halo shut down", "halo shutdown", "halo off", "hello close", "hello shut down", "hello shutdown", "hello off", "hey close", "hey shut down", "hey shutdown", "hey off"]):
            print("Voice shutdown command detected")
            self.voice_controller.shutdown.emit()
            return True
        
        # Deactivate all features
        if self.matches_command(text, ["halo deactivate", "hello deactivate", "hey deactivate", "halo deactivate all", "hello deactivate all", "hey deactivate all"]):
            print("Voice deactivate all command detected")
            self.deactivate_all_toggles()
            return True
        
        # Copy chatbot text
        if self.matches_command(text, ["halo copy", "hello copy", "hey copy", "halo copy text", "hello copy text", "hey copy text", "halo coffee", "hello coffee", "hey coffee"]):
            print("Voice copy command detected")
            self.copy_chatbot_text()
            return True
        
        # Paste clipboard content (be careful about similar words like "praise", "pays")
        if self.matches_paste_command(text):
            print("Voice paste command detected")
            self.paste_clipboard_content()
            return True
        
        # Press Enter key (works with or without halo prefix)
        if self.matches_command(text, ["halo enter", "hello enter", "hey enter", "halo return", "hello return", "hey return", "enter", "return"]):
            print("Voice enter command detected")
            self.press_enter_key()
            return True
        
        # Start voice typing
        if self.matches_command(text, ["halo type", "hello type", "hey will type", "hello will type", "hey type", "he'll type"]):
            self.voice_controller.start_typing.emit()
            return True
            
        # Start AI chat typing
        if self.matches_command(text, ["halo help", "hello help", "hey help", "he will help", "halo chat", "hello chat", "hey chat"]):
            self.voice_controller.start_ai_typing.emit()
            return True
            
        # Remove one word
        if self.matches_command(text, ["halo back", "hello back", "hey back", "hey look back", "he looked back", "halo remove", "hello remove"]):
            if self.voice_controller.voice_typing:
                self.voice_controller.back.emit()
            elif self.voice_controller.ai_typing:
                self.remove_last_ai_word()
            else:
                self.perform_ctrl_backspace()
            return True
            
        # If not in typing mode, ignore other commands
        if not self.voice_controller.voice_typing and not self.voice_controller.ai_typing:
            return False
            
        # Redo entire sentence
        if self.matches_command(text, ["halo redo", "halo we do", "hello redo", "hey redo", "halo repeat", "hello repeat", "hillary do"]):
            if self.voice_controller.voice_typing:
                self.voice_controller.redo.emit()
            elif self.voice_controller.ai_typing:
                self.redo_ai_sentence()
            return True
            
        # Insert current text and clear
        if self.matches_command(text, ["halo in", "hello in", "hey in", "halo insert", "hello insert"]):
            if self.voice_controller.voice_typing:
                self.voice_controller.insert.emit()
            elif self.voice_controller.ai_typing:
                self.insert_ai_and_clear()
            return True
            
        # Stop typing and finalize
        if self.matches_command(text, ["halo stop", "halo done", "halo don't", "hello stop", "hello done", "hey stop", "hey done", "hey hilton", "he looked on", "halo finish", "hello finish"]):
            if self.voice_controller.voice_typing:
                self.voice_controller.finish_typing.emit()
            elif self.voice_controller.ai_typing:
                self.voice_controller.finish_ai_typing.emit()
            return True
            
        # Add to current sentence
        if self.voice_controller.voice_typing:
            self.voice_controller.add_word.emit(text)
            return True
        elif self.voice_controller.ai_typing:
            self.voice_controller.add_ai_word.emit(text)
            return True
            
        return False
    
    def matches_command(self, text: str, commands: list) -> bool:
        """Check if text matches any of the command variations"""
        text_lower = text.lower().strip()
        
        for command in commands:
            # Direct match
            if command in text_lower:
                return True
            
            # Fuzzy match - check if most words match
            text_words = set(text_lower.split())
            command_words = set(command.split())
            
            # If at least 70% of command words are present, consider it a match
            if len(command_words) > 0:
                match_ratio = len(text_words.intersection(command_words)) / len(command_words)
                if match_ratio >= 0.7:
                    return True
        
        return False
    
    def matches_paste_command(self, text: str) -> bool:
        """Check if text matches paste command, avoiding similar words like 'praise', 'pays'"""
        text_lower = text.lower().strip()
        
        # Exact matches for paste command
        paste_commands = [
            "halo paste",
            "hello paste", 
            "hey paste",
            "halo paste text",
            "hello paste text",
            "hey paste text"
        ]
        
        # Check for exact matches first
        for command in paste_commands:
            if command == text_lower:
                return True
            
            # Check if the command is contained in the text with word boundaries
            if command in text_lower:
                # Make sure it's not part of another word (like "praise" containing "raise")
                words = text_lower.split()
                command_words = command.split()
                
                # Find if all command words appear consecutively
                for i in range(len(words) - len(command_words) + 1):
                    if words[i:i+len(command_words)] == command_words:
                        return True
        
        # More lenient matching - but exclude problematic words
        excluded_words = ["praise", "prays", "pays", "pace", "place", "base"]
        
        # Check if text contains any excluded words
        for excluded in excluded_words:
            if excluded in text_lower:
                return False
        
        # Now check for fuzzy paste matching
        if ("halo" in text_lower or "hello" in text_lower or "hey" in text_lower):
            # Look for words that sound like "paste"
            paste_variants = ["paste", "past", "passed"]
            for variant in paste_variants:
                if variant in text_lower:
                    return True
        
        return False
    
    def perform_ctrl_backspace(self):
        """Perform Ctrl+Backspace to delete the previous word"""
        if pyautogui:
            try:
                pyautogui.hotkey('ctrl', 'backspace')
                self.play_back_sound()
                print("Performed Ctrl+Backspace")
            except Exception as e:
                print(f"Error performing Ctrl+Backspace: {e}")
    
    def start_voice_typing(self):
        """Start voice typing mode"""
        self.voice_controller.voice_typing = True
        self.voice_controller.sentence = ""
        self.voice_window.show_typing_window()
        self.voice_window.update_sentence("")
        self.voice_window.update_status("🎤 Listening... Say 'halo done' to finish")
        self.play_beep_sound()  # Play beep sound when starting voice typing
        print("Voice typing mode started")
    
    def add_to_sentence(self, text: str):
        """Add words to the current sentence being typed"""
        # Filter out command words
        words_to_ignore = ["halo", "hello", "hey", "type", "redo", "back", "stop", "done", "in", "insert", "will"]
        words = text.split()
        filtered_words = [word for word in words if word not in words_to_ignore]
        
        if filtered_words:
            if self.voice_controller.sentence:
                self.voice_controller.sentence += " " + " ".join(filtered_words)
            else:
                self.voice_controller.sentence = " ".join(filtered_words)
            
            self.voice_window.update_sentence(self.voice_controller.sentence)
    
    def redo_sentence(self):
        """Clear the current sentence and start over"""
        self.voice_controller.sentence = ""
        self.voice_window.update_sentence("")
        self.voice_window.update_status("🎤 Sentence cleared. Continue speaking...")
        self.play_back_sound()
        print("Sentence cleared for redo")
    
    def remove_last_word(self):
        """Remove the last word from the current sentence"""
        if self.voice_controller.sentence:
            words = self.voice_controller.sentence.split()
            if words:
                words.pop()
                self.voice_controller.sentence = " ".join(words)
                self.voice_window.update_sentence(self.voice_controller.sentence)
                self.voice_window.update_status("🎤 Last word removed. Continue speaking...")
                self.play_back_sound()
                print("Last word removed")
    
    def finish_voice_typing(self):
        """Finish voice typing and type the sentence"""
        if self.voice_controller.sentence.strip():
            self.voice_window.update_status("⏱️ Typing in 2 seconds...")
            
            # Play beep sound for typing
            self.play_beep_sound()
            
            # Use QTimer for delay before typing (runs on main thread)
            QTimer.singleShot(2000, self.type_sentence)  # 2 second delay
        else:
            self.stop_voice_typing()
    
    def insert_and_clear(self):
        """Insert current text immediately and clear the sentence but stay in typing mode"""
        if self.voice_controller.sentence.strip():
            # Add proper punctuation and spacing
            formatted_text = self.format_text_for_typing(self.voice_controller.sentence, is_final=False)
            
            # Type the formatted sentence immediately
            if pyautogui:
                try:
                    pyautogui.write(formatted_text)
                    print(f"Inserted: {formatted_text}")
                except Exception as e:
                    print(f"Error inserting text: {e}")
            
            # Clear the sentence but stay in typing mode
            self.voice_controller.sentence = ""
            self.voice_window.update_sentence("")
            self.voice_window.update_status("🎤 Text inserted. Continue speaking...")
            self.play_beep_sound()
            print("Text inserted and cleared, continuing in typing mode")
    
    def format_text_for_typing(self, text: str, is_final: bool = False) -> str:
        """Format text with proper punctuation and spacing"""
        if not text.strip():
            return text
            
        # Clean up the text
        formatted_text = text.strip()
        
        # Capitalize first letter if it's not already
        if formatted_text and formatted_text[0].islower():
            formatted_text = formatted_text[0].upper() + formatted_text[1:]
        
        # Check if text already ends with punctuation
        punctuation_marks = '.!?;:'
        has_punctuation = any(formatted_text.endswith(mark) for mark in punctuation_marks)
        
        if not has_punctuation:
            # Determine appropriate punctuation
            question_words = ['what', 'where', 'when', 'why', 'how', 'who', 'which', 'whose', 'whom']
            text_lower = formatted_text.lower()
            
            # Check if it's a question
            if (any(text_lower.startswith(word) for word in question_words) or 
                'is ' in text_lower[:10] or 'are ' in text_lower[:10] or 
                'do ' in text_lower[:10] or 'does ' in text_lower[:10] or
                'can ' in text_lower[:10] or 'could ' in text_lower[:10] or
                'will ' in text_lower[:10] or 'would ' in text_lower[:10]):
                formatted_text += '?'
            else:
                formatted_text += '.'
        
        # Add appropriate spacing after
        if is_final:
            # For final typing (halo done), add extra space for new sentence
            formatted_text += ' '
        else:
            # For halo in, add space to continue the paragraph
            formatted_text += ' '
            
        return formatted_text
    
    def play_beep_sound(self):
        """Play beep sound for typing commands"""
        self.play_sound("SFX/beep.mp3")
    
    def play_back_sound(self):
        """Play back sound for redo/back commands"""
        self.play_sound("SFX/back.mp3")
    
    def play_sound(self, sound_file):
        """Play a sound file using pygame"""
        if not HAS_AUDIO:
            print("Beep!")
            return
            
        try:
            sound_path = os.path.join(os.path.dirname(__file__), sound_file)
            if os.path.exists(sound_path):
                sound = pygame.mixer.Sound(sound_path)
                sound.play()
                print(f"Playing: {sound_file}")
            else:
                print(f"Sound not found: {sound_path}")
                print("Beep!")
        except Exception as e:
            print(f"Sound error: {e}")
    
    def type_sentence(self):
        """Type the sentence using pyautogui"""
        if pyautogui and self.voice_controller.sentence:
            try:
                # Add proper punctuation and spacing for final sentence
                formatted_text = self.format_text_for_typing(self.voice_controller.sentence, is_final=True)
                pyautogui.write(formatted_text)
                print(f"Typed: {formatted_text}")
            except Exception as e:
                print(f"Error typing sentence: {e}")
        
        self.stop_voice_typing()
    
    def stop_voice_typing(self):
        """Stop voice typing mode"""
        self.voice_controller.voice_typing = False
        self.voice_controller.sentence = ""
        self.voice_window.hide_typing_window()
        print("Voice typing mode stopped")
    
    # AI Chat Typing Methods
    def start_ai_typing(self):
        """Start AI chat typing mode"""
        # Ensure AI agent is enabled
        if not self.states.get('ai_agent', False):
            # Enable AI agent automatically
            self.ai_btn.setChecked(True)
            self.states['ai_agent'] = True
            self.toggle_chat_interface(True)
            self.update_toggle_style(self.ai_btn)
            self.update_status()
            
        self.voice_controller.ai_typing = True
        self.voice_controller.ai_sentence = ""
        self.voice_window.show_typing_window()
        self.voice_window.update_sentence("")
        self.voice_window.update_status("🤖 AI Chat Mode - Say 'halo done' to finish")
        # Update header to show AI mode
        self.voice_window.header.setText("🤖 AI Chat Typing")
        self.play_beep_sound()
        print("AI chat typing mode started")
    
    def add_to_ai_sentence(self, text: str):
        """Add words to the current AI chat sentence being typed"""
        # Filter out command words
        words_to_ignore = ["halo", "hello", "hey", "help", "chat", "redo", "back", "look", "looked", "stop", "done", "hilton", "on", "in", "insert", "will"]
        words = text.split()
        filtered_words = [word for word in words if word not in words_to_ignore]
        
        if filtered_words:
            if self.voice_controller.ai_sentence:
                self.voice_controller.ai_sentence += " " + " ".join(filtered_words)
            else:
                self.voice_controller.ai_sentence = " ".join(filtered_words)
            
            self.voice_window.update_sentence(self.voice_controller.ai_sentence)
    
    def redo_ai_sentence(self):
        """Clear the current AI sentence and start over"""
        self.voice_controller.ai_sentence = ""
        self.voice_window.update_sentence("")
        self.voice_window.update_status("🤖 AI sentence cleared. Continue speaking...")
        self.play_back_sound()
        print("AI sentence cleared for redo")
    
    def remove_last_ai_word(self):
        """Remove the last word from the current AI sentence"""
        if self.voice_controller.ai_sentence:
            words = self.voice_controller.ai_sentence.split()
            if words:
                words.pop()
                self.voice_controller.ai_sentence = " ".join(words)
                self.voice_window.update_sentence(self.voice_controller.ai_sentence)
                self.voice_window.update_status("🤖 Last word removed. Continue speaking...")
                self.play_back_sound()
                print("Last AI word removed")
    
    def insert_ai_and_clear(self):
        """Insert current AI text immediately and clear the sentence but stay in AI typing mode"""
        if self.voice_controller.ai_sentence.strip():
            # Add the text directly to the chat input
            current_text = self.chat_input.toPlainText()
            if current_text and not current_text.endswith(' '):
                current_text += " "
            
            formatted_text = self.voice_controller.ai_sentence.strip()
            # Capitalize first letter if it's the start of the input
            if not current_text.strip():
                formatted_text = formatted_text.capitalize()
            
            self.chat_input.setPlainText(current_text + formatted_text + " ")
            
            # Clear the sentence but stay in AI typing mode
            self.voice_controller.ai_sentence = ""
            self.voice_window.update_sentence("")
            self.voice_window.update_status("🤖 Text added to chat. Continue speaking...")
            self.play_beep_sound()
            print("Text added to AI chat input, continuing in AI typing mode")
    
    def finish_ai_typing(self):
        """Finish AI typing, add the sentence to chat input, and send to AI"""
        if self.voice_controller.ai_sentence.strip():
            current_text = self.chat_input.toPlainText()
            if current_text and not current_text.endswith(' '):
                current_text += " "
            
            # Format the sentence nicely
            formatted_text = self.voice_controller.ai_sentence.strip()
            
            # Capitalize first letter if it's the start of the input
            if not current_text.strip():
                formatted_text = formatted_text.capitalize()
            
            # Add to chat input
            final_message = current_text + formatted_text
            self.chat_input.setPlainText(final_message)
            
            self.voice_window.update_status("🚀 Sending to AI...")
            self.play_beep_sound()
            
            print(f"AI chat text added and sending: {final_message}")
            
            # Stop AI typing mode first to prevent interference
            self.stop_ai_typing()
            
            # Automatically send the message to AI
            self.send_message()
        else:
            # Stop AI typing mode even if no text
            self.stop_ai_typing()
    
    def stop_ai_typing(self):
        """Stop AI chat typing mode"""
        self.voice_controller.ai_typing = False
        self.voice_controller.ai_sentence = ""
        self.voice_window.hide_typing_window()
        # Reset header back to normal
        self.voice_window.header.setText("🎤 Voice Typing")
        print("AI chat typing mode stopped")
    
    def update_chat_input_from_voice(self, text: str):
        """Update chat input from voice thread via signal (runs on main thread)"""
        # This method is no longer used - voice input only goes to chat via typing modes
        pass
    
    # Mouse action methods removed - now handled by VoiceController

    def update_status(self, message=None):
        """Update status bar with active features or custom message"""
        if message:
            self.status.setText(message)
            return
            
        active = []
        
        for key, is_active in self.states.items():
            if is_active:
                name = key.replace('_', ' ').title()
                color = self.colors[key]
                active.append(f'<span style="color: {color};">●</span> {name}')
        
        if active:
            text = f'<b>Active:</b> {" | ".join(active)}'
        else:
            text = '<span style="color: #7f8c8d;">Ready</span>'
        
        self.status.setText(text)
        
    def send_message(self):
        """Handle sending a message"""
        message = self.chat_input.toPlainText().strip()
        if not message:
            return
        
        # Show chat display when user sends first message
        if not self.chat_display.isVisible():
            self.chat_display.setVisible(True)
        
        # Add user message to chat
        current_text = self.chat_display.toPlainText()
        if current_text:
            current_text += "\n\n\n"
        
        user_message = f"You: {message}\n"
        
        # Simple AI response simulation (replace with actual AI integration)
        ai_response = self.chat.generate_response(message)
        
        # Update chat display
        self.chat_display.setPlainText(current_text + user_message + "\n" + 'HALO: ' + ai_response)
        
        # Scroll to bottom
        self.chat_display.verticalScrollBar().setValue(
            self.chat_display.verticalScrollBar().maximum()
        )
        
        # Clear input
        self.chat_input.clear()
        
        print(f"User message: {message}")
        print(f"HALO response: {ai_response}")

    def update_toggle_style(self, toggle):
        """Update toggle switch styling"""
        if not hasattr(toggle, 'active_color'):
            # Skip styling for toggles without active_color (like chat_voice_btn)
            return
            
        if toggle.isChecked():
            toggle.setStyleSheet(f"""
                QCheckBox {{
                    background: {toggle.active_color};
                    color: white;
                }}
                QCheckBox:hover {{
                    background: {toggle.active_color};
                }}
            """)
        else:
            toggle.setStyleSheet("")

    def on_toggle(self, toggle, checked):
        """Handle toggle switch changes"""
        key = toggle.state_key
        self.states[key] = checked
        
        # Sync voice buttons
        if key == 'voice':
            for other in (getattr(self, 'voice_btn', None), getattr(self, 'chat_voice_btn', None)):
                if other and other is not toggle:
                    other.blockSignals(True)
                    other.setChecked(checked)
                    if hasattr(other, 'state_key'):
                        self.update_toggle_style(other)
                    other.blockSignals(False)
        
        # Handle toggle
        self.handle_toggle(key, checked)
        
        # Update UI
        self.update_toggle_style(toggle)
        self.update_status()
        
        # Log
        state = 'activated' if checked else 'deactivated'
        print(f"{toggle.text()} {state}")
        active = [k.replace('_', ' ').title() for k, v in self.states.items() if v]
        print(f"Active features: {active}")


    def handle_toggle(self, key, state):
        """Handle feature toggle changes"""
        handlers = {
            'face_tracking': (self.start_face_tracking, self.stop_face_tracking),
            'voice': (self.start_voice, self.stop_voice),
            'ai_agent': (lambda: self.toggle_chat_interface(True),
                        lambda: self.toggle_chat_interface(False)),
            'performance_mode': (self.enable_fast_mode, self.enable_power_saving),
        }
        
        # Show/hide performance button with face tracking
        if key == 'face_tracking':
            self.perf_btn.setVisible(state)
            if not state:
                self.perf_btn.setChecked(False)
                self.states['performance_mode'] = False
                self.update_toggle_style(self.perf_btn)
        
        start_fn, stop_fn = handlers.get(key, (None, None))
        if start_fn:
            start_fn() if state else stop_fn()
        else:
            print(f"Unknown toggle: {key}")


    def start_face_tracking(self):
        """Start face tracking"""
        if not hasattr(self, 'tracker') or self.tracker is None:
            fast_mode = self.states.get('performance_mode', False)
            self.tracker = HeadMouseTracker(fast_mode=fast_mode)
            self.tracker.start(block=False)
            mode = 'fast' if fast_mode else 'power saving'
            print(f"Face tracking started ({mode} mode)")
    
    def stop_face_tracking(self):
        """Stop face tracking"""
        if hasattr(self, 'tracker') and self.tracker:
            try:
                self.tracker.stop()
            finally:
                self.tracker = None
            print("Face tracking stopped")


    def start_voice(self):
        """Start voice recognition"""
        if not hasattr(self, 'recognizer') or self.recognizer is None:
            self.recognizer = VoskMicRecognizer(
                model="language_models/eng_model", 
                on_result=self.handle_voice_result
            )
            self.recognizer.start(background=True)
            print("Voice recognition started")
    
    def stop_voice(self):
        """Stop voice recognition"""
        if hasattr(self, 'recognizer') and self.recognizer:
            try:
                self.recognizer.stop()
            finally:
                self.recognizer = None
            print("Voice recognition stopped")

    def enable_fast_mode(self):
        """Enable fast performance mode"""
        if hasattr(self, 'tracker') and self.tracker:
            self.tracker.set_performance_mode(True)
        print("Fast mode enabled")
    
    def enable_power_saving(self):
        """Enable power saving mode"""
        if hasattr(self, 'tracker') and self.tracker:
            self.tracker.set_performance_mode(False)
        print("Power saving mode enabled")


    def start_chat(self):
        """Initialize chat system"""
        self.chat = HaloChat()
        self.chat.start()
        print("Chat system initialized")

    def toggle_chat_interface(self, show_chat):
        """Show or hide the AI agent interface and move buttons up to make space"""
        self.chat_widget.setVisible(show_chat)
        
        if show_chat:
            # Show chat display only when user starts chatting
            self.chat_display.setVisible(False)  # Keep hidden initially
            
            # Move all control buttons up by reducing their spacing and margins
            # This gives more room for the AI agent interface
            layout = self.content.layout()
            if layout:
                # Reduce spacing between buttons when chat is open
                layout.setSpacing(12)  # Reduced from 18
                
                # Adjust margins to create more space
                layout.setContentsMargins(20, 15, 20, 15)  # Reduced top/bottom margins
            
        else:
            self.chat_display.setVisible(False)
            self.chat_display.clear()
            
            # Restore normal spacing when chat is closed
            layout = self.content.layout()
            if layout:
                layout.setSpacing(18)  # Original spacing
                layout.setContentsMargins(25, 25, 25, 25)  # Original margins
    
    
    def toggle_sidebar(self):
        """Toggle sidebar expansion/collapse"""
        if self.expanded:
            self.collapse_sidebar()
        else:
            self.expand_sidebar()
    
    def collapse_sidebar(self):
        """Collapse the entire window into circular HALO"""
        if not self.expanded:
            return
            
        self.expanded = False
        
        # Hide all content - only show the button
        self.content.setVisible(False)
        
        # First change to frameless to remove window decorations
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Transform button to fill entire circular window
        self.toggle_btn.setFixedSize(self.width_collapsed, self.width_collapsed)
        
        # Try to set logo icon for collapsed state
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'imgs', 'logo.png')
            if os.path.exists(logo_path):
                # Create icon from PNG and set it
                icon = QIcon(logo_path)
                self.toggle_btn.setIcon(icon)
                self.toggle_btn.setIconSize(QSize(40, 40))
                self.toggle_btn.setText("")  # Remove text when using icon
            else:
                self.toggle_btn.setText("HALO")  # Fallback text
        except Exception as e:
            print(f"Could not load collapsed button logo: {e}")
            self.toggle_btn.setText("HALO")  # Fallback text
            
        self.update_circular_halo_style()
        
        # Apply circular mask
        self.apply_circular_mask()
        
        # Enable mouse tracking for dragging in collapsed state
        self.setMouseTracking(True)
        self.toggle_btn.setMouseTracking(True)
        
        # Show the window again after changing flags
        self.show()
        
        # Set the geometry for collapsed state
        screen = QApplication.primaryScreen().availableGeometry()
        new_x = screen.width() - self.width_collapsed
        new_y = (screen.height() - self.width_collapsed) // 2
        
        self.setFixedSize(self.width_collapsed, self.width_collapsed)
        self.move(new_x, new_y)
    
    def expand_sidebar(self):
        """Expand the window from circular HALO to full panel"""
        if self.expanded:
            return
            
        self.expanded = True
        
        # Remove circular mask first
        self.clearMask()
        
        # Restore window frame (make it movable again)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # Show the window again after changing flags
        self.show()
        
        # Restore window to full panel size and position
        screen = QApplication.primaryScreen().availableGeometry()
        new_x = screen.width() - self.width_expanded
        self.setFixedSize(self.width_expanded, self.height)
        self.move(new_x, self.top_margin)
        
        # Show the main content
        self.content.setVisible(True)
        
        # Transform button back to arrow
        self.toggle_btn.setFixedSize(35, 90)  # Original size
        self.toggle_btn.setText("▶")  # Right arrow pointing inward when expanded
        self.toggle_btn.setIcon(QIcon())  # Clear icon
        
        # Reload the main stylesheet to restore normal styling
        self.load_stylesheet()
        
        # Apply proper toggle button styling
        self.apply_toggle_button_style()
    
    def enterEvent(self, event):
        """Mouse entered the widget"""
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Mouse left the widget"""
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            # When expanded, only allow dragging from title area
            if self.expanded:
                if event.position().y() <= 80:
                    self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    event.accept()
                    return
            else:
                # When collapsed, allow dragging from anywhere
                self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            new_pos = event.globalPosition().toPoint() - self.drag_pos
            self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def update_circular_halo_style(self):
        """Apply circular HALO styling when collapsed"""
        # Style for the button to fill the entire circular window
        button_style = """
            QPushButton {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8,
                    stop:0 #87CEEB, stop:0.7 #4682B4, stop:1 #2E8B57);
                color: white;
                border: none;
                border-radius: 40px;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
                text-align: center;
            }
            QPushButton:hover {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.8,
                    stop:0 #ADD8E6, stop:0.7 #87CEEB, stop:1 #4682B4);
            }
        """
        self.toggle_btn.setStyleSheet(button_style)
        
        # Style for the main window to be transparent/circular
        window_style = """
            QMainWindow {
                background: transparent;
                border: none;
            }
        """
        self.setStyleSheet(window_style)
    
    def apply_circular_mask(self):
        """Apply a circular mask to make the window truly circular"""
        from PySide6.QtGui import QRegion
        
        # Create circular region
        region = QRegion(0, 0, self.width_collapsed, self.width_collapsed, QRegion.Ellipse)
        self.setMask(region)
    
    def apply_toggle_button_style(self):
        """Apply proper styling to the toggle button"""
        toggle_style = """
            QPushButton#toggle_btn {
                background: #0066FF;
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.8);
                font-size: 20px;
                font-weight: bold;
                border-radius: 0px;
            }
            QPushButton#toggle_btn:hover {
                background: #0044CC;
                border: 2px solid rgba(255, 255, 255, 1.0);
            }
        """
        self.toggle_btn.setStyleSheet(toggle_style)
    
    def load_stylesheet(self):
        """Load the external stylesheet"""
        try:
            stylesheet_path = os.path.join(os.path.dirname(__file__), 'styles.qss')
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
        except FileNotFoundError:
            print("Warning: styles.qss file not found. Using default styling.")
        except Exception as e:
            print(f"Error loading stylesheet: {e}")
    
    def apply_stylesheet_to_widget(self, widget):
        """Reapply the main stylesheet to ensure widget styling is updated"""
        try:
            stylesheet_path = os.path.join(os.path.dirname(__file__), 'styles.qss')
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
        except Exception as e:
            print(f"Error reapplying stylesheet: {e}")

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    app.setApplicationName("HALO - Vision & AI Assistant")
    app.setApplicationVersion("1.0")
    
    # Set app icon
    try:
        logo_path = os.path.join(os.path.dirname(__file__), 'imgs', 'logo.png')
        if os.path.exists(logo_path):
            app.setWindowIcon(QIcon(logo_path))
    except Exception as e:
        print(f"App icon error: {e}")
    
    # Create and show main window
    window = HaloApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
