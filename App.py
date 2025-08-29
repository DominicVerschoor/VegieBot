import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QLabel, QFrame, QHBoxLayout, QTextEdit, 
                               QLineEdit, QScrollArea, QSizePolicy, QCheckBox)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, QRect, QObject, Signal
from PySide6.QtGui import QFont, QPalette, QColor
import json
import os
import re
try:
    import pyautogui
except ImportError:
    print("Warning: pyautogui not installed. Voice mouse commands will not work.")

from MonitorTracking import HeadMouseTracker
from VoiceControl import VoskMicRecognizer
from Chatbot import HaloChat

#Please put future CSS changes in styles.qss

class VoiceController(QObject):
    """Thread-safe controller for voice commands using Qt signals"""
    left_click_signal = Signal()
    right_click_signal = Signal()
    middle_click_signal = Signal()
    shift_click_signal = Signal()
    update_chat_input_signal = Signal(str)  # For adding text to chat input
    
    def __init__(self):
        super().__init__()
        # Connect signals to slot methods
        self.left_click_signal.connect(self.do_left_click)
        self.right_click_signal.connect(self.do_right_click)
        self.middle_click_signal.connect(self.do_middle_click)
        self.shift_click_signal.connect(self.do_shift_click)
    
    def do_left_click(self):
        """Perform left click on main thread"""
        if pyautogui:
            pyautogui.click()
    
    def do_right_click(self):
        """Perform right click on main thread"""
        if pyautogui:
            pyautogui.rightClick()
    
    def do_middle_click(self):
        """Perform middle click on main thread"""
        if pyautogui:
            pyautogui.middleClick()
    
    def do_shift_click(self):
        """Perform shift+click on main thread"""
        if pyautogui:
            pyautogui.keyDown('shift')
            pyautogui.click()
            pyautogui.keyUp('shift')

class CollapsibleSidebar(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HALO Control Panel - Drag to Move")
        self.expanded_width = 320
        self.collapsed_width = 80  # Size for circular HALO button
        
        # Get screen dimensions - leave space at top and bottom
        screen = QApplication.primaryScreen().availableGeometry()
        self.margin_top = 50    # Space at top for browser tabs, etc.
        self.margin_bottom = 50 # Space at bottom for taskbar, etc.
        self.base_height = screen.height() - self.margin_top - self.margin_bottom
        self.chat_height = 300
        self.window_height = self.base_height
        
        # Button states with heavenly color scheme
        self.button_states = {
            'face_tracking': False,
            'colorblind': False,
            'ai_agent': False
        }
        
        # Heavenly blue color palette
        self.button_colors = {
            'face_tracking': '#87CEEB',   # Sky blue
            'colorblind': '#DDA0DD',     # Plum (soft purple)
            'ai_agent': '#FFE4B5'        # Moccasin (soft golden)
        }
        
        # Set window properties - make it movable
        self.setFixedSize(self.expanded_width, self.window_height)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)  # Removed FramelessWindowHint to make it movable
        
        # Position window on right side with margins
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.expanded_width, self.margin_top)
        
        # Set up the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create main horizontal layout
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Initially expanded (define this early)
        self.is_expanded = True
        
        # Create sliding toggle button with arrow (restored)
        self.toggle_btn = QPushButton("◀")  # Left arrow when expanded
        self.toggle_btn.setObjectName("toggle_btn")
        self.toggle_btn.setFixedSize(35, 90)
        self.toggle_btn.clicked.connect(self.toggle_sidebar)
        
        # Create content widget
        self.content_widget = QWidget()
        self.content_widget.setFixedWidth(self.expanded_width - 30)
        
        # Create content layout
        layout = QVBoxLayout(self.content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Create top section with status and close button
        top_section = QWidget()
        top_layout = QVBoxLayout(top_section)
        top_layout.setContentsMargins(10, 10, 10, 5)
        
        # Header with title and close button
        header_layout = QHBoxLayout()
        
        # Add heavenly title
        title_label = QLabel(" HALO ")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        
        # Add heavenly close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("close_btn")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.clicked.connect(self.close_application)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        
        # Heavenly status bar
        self.status_label = QLabel()
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignLeft)
        self.update_status_bar()
        
        top_layout.addLayout(header_layout)
        top_layout.addWidget(self.status_label)
        
        layout.addWidget(top_section)
        
        # Add heavenly separator line
        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        
        # Add stretch to center the buttons vertically
        layout.addStretch()
        
        # Create toggle switches without emojis
        self.face_tracking_btn = self.create_toggle_switch(
            "Face Tracking", 
            "#87CEEB",  # Sky blue
            "#4682B4",  # Steel blue
            "",
            'face_tracking'
        )
        self.colorblind_btn = self.create_toggle_switch(
            "Colorblind Mode", 
            "#DDA0DD",  # Plum
            "#BA55D3",  # Medium orchid
            "",
            'colorblind'
        )
        self.ai_agent_btn = self.create_toggle_switch(
            "AI Agent", 
            "#FFE4B5",  # Moccasin
            "#DEB887",  # Burlywood
            "",
            'ai_agent'
        )
        self.voice_btn = self.create_toggle_switch(
            "Voice Detection", 
            "#F0E68C",  # Khaki (soft yellow)
            "#DAA520",  # Goldenrod
            "",
            'voice'
        )
        # Add voice button state and color to button_states and button_colors
        self.button_states['voice'] = False
        self.button_colors['voice'] = '#F0E68C'
        
        # Add buttons to layout
        layout.addWidget(self.face_tracking_btn)
        layout.addWidget(self.colorblind_btn)
        layout.addWidget(self.ai_agent_btn)
        layout.addWidget(self.voice_btn)

        # Add stretch to center the buttons vertically
        layout.addStretch()
        
        # Create heavenly chat interface (initially hidden)
        self.chat_widget = self.create_chat_interface()
        self.chat_widget.setVisible(False)
        layout.addWidget(self.chat_widget)
        
        # Add bottom stretch
        layout.addStretch()
        
        # Add widgets to main layout
        main_layout.addWidget(self.toggle_btn, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        main_layout.addWidget(self.content_widget)
        
        # Set up animation for sidebar
        self.sidebar_animation = QPropertyAnimation(self, b"geometry")
        self.sidebar_animation.setDuration(200)
        self.sidebar_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Set up animation for chat
        self.chat_animation = QPropertyAnimation(self, b"geometry")
        self.chat_animation.setDuration(300)
        self.chat_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        
        # Initialize thread-safe voice controller
        self.voice_controller = VoiceController()
        # Connect the chat input signal
        self.voice_controller.update_chat_input_signal.connect(self.update_chat_input_from_voice)
        
        # Variables for drag functionality
        self.drag_position = None
        
        # Load external stylesheet
        self.load_stylesheet()
        
        self._start_chat()
        
        # Enable mouse tracking for hover detection
        self.setMouseTracking(True)
        self.toggle_btn.setMouseTracking(True)
    
    def create_toggle_switch(self, text, color, active_color, emoji, state_key):
        """Create a toggle switch with solid colors"""
        display_text = f"{emoji} {text}" if emoji else text
        switch = QCheckBox(display_text)
        switch.setMinimumHeight(60)
        switch.setFont(QFont("Segoe UI", 14, QFont.Bold))
        
        # Store the colors and state key
        switch.normal_color = color
        switch.active_color = active_color
        switch.state_key = state_key
        
        self.update_switch_style(switch)
        switch.toggled.connect(lambda checked: self.on_switch_toggled(switch, checked))
        
        return switch
    
    def close_application(self):
        """Close the entire application"""
        print("Application closing...")
        QApplication.quit()

    def create_chat_interface(self):
        """Create the chat interface widget"""
        chat_container = QWidget()
        chat_container.setObjectName("chat_container")
        chat_container.setFixedHeight(self.chat_height)
        
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(8)
        
        # Heavenly chat header
        chat_header = QLabel(" AI Assistant ")
        chat_header.setObjectName("chat_header")
        chat_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        chat_layout.addWidget(chat_header)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chat_display")
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(60)
        self.chat_display.setPlaceholderText("AI responses will appear here...")
        chat_layout.addWidget(self.chat_display)
        
        # Input area - separate rows for text input and buttons
        # First row: text input (larger)
        self.chat_input = QTextEdit()
        self.chat_input.setObjectName("chat_input")
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.setMaximumHeight(60)
        self.chat_input.setMinimumHeight(40)
        # Connect Enter key to send message
        def on_key_press(event):
            if event.key() == Qt.Key_Return and not event.modifiers():
                self.send_message()
            else:
                QTextEdit.keyPressEvent(self.chat_input, event)
        self.chat_input.keyPressEvent = on_key_press
        
        self.chat_voice_btn = QPushButton("🎤")
        self.chat_voice_btn.setObjectName("chat_voice_btn")
        self.chat_voice_btn.setFixedSize(70, 70)
        self.chat_voice_btn.setCheckable(True)
        self.chat_voice_btn.setToolTip("Voice input")

        
        send_btn = QPushButton("Send")
        send_btn.setObjectName("send_btn")
        send_btn.setFixedWidth(100)
        send_btn.clicked.connect(self.send_message)
        
        # Add text input to chat layout
        chat_layout.addWidget(self.chat_input)
        
        # Second row: buttons with reduced spacing
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)  # Reduce spacing between buttons
        button_layout.addStretch()  # Push buttons to right
        button_layout.addWidget(self.chat_voice_btn)
        button_layout.addWidget(send_btn)
        
        chat_layout.addLayout(button_layout)
        
        self.chat_voice_btn.toggled.connect(self.toggle_voice_input)
        # Store state key for consistency with other switches
        self.chat_voice_btn.state_key = 'voice'
        
        return chat_container
    
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
        
        # Check for mouse commands first
        if self.process_voice_mouse_command(text):
            return  # Command processed, don't add to chat input
            
        # Add to chat input using signal (thread-safe)
        formatted_text = f'{text}. '
        self.voice_controller.update_chat_input_signal.emit(formatted_text)
    
    def process_voice_mouse_command(self, text: str) -> bool:
        """Process voice commands for mouse actions. Returns True if command was processed."""
        if not pyautogui:
            return False
            
        # Define mouse command patterns with Qt signals
        mouse_commands = {
            r'^click$': self.voice_controller.left_click_signal,  # Simple "click" = left click
            r'^left\s*click$': self.voice_controller.left_click_signal,
            r'^right\s*click$': self.voice_controller.right_click_signal, 
            r'^middle\s*click$': self.voice_controller.middle_click_signal,
            r'^middle\s*mouse$': self.voice_controller.middle_click_signal,
            r'^shift\s*\+\s*click$': self.voice_controller.shift_click_signal,
            r'^shift\s*click$': self.voice_controller.shift_click_signal
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
    
    def update_chat_input_from_voice(self, text: str):
        """Update chat input from voice thread via signal (runs on main thread)"""
        current_text = self.chat_input.toPlainText()
        self.chat_input.setPlainText(current_text + text)
    
    # Mouse action methods removed - now handled by VoiceController

    def update_status_bar(self):
        """Update the status bar with active features and their colors"""
        active_features = []
        
        for key, is_active in self.button_states.items():
            if is_active:
                feature_name = key.replace('_', ' ').title()
                color = self.button_colors[key]
                # Create HTML with colored indicator
                active_features.append(f'<span style="color: {color};">●</span> {feature_name}')
        
        if active_features:
            status_html = f'<b>Active:</b> {" | ".join(active_features)}'
        else:
            status_html = '<span style="color: #7f8c8d;">Ready</span>'
        
        self.status_label.setText(status_html)
        
    def send_message(self):
        """Handle sending a message"""
        message = self.chat_input.toPlainText().strip()
        if not message:
            return
        
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

    def update_switch_style(self, switch):
        """Update toggle switch style with solid colors based on checked/unchecked state"""
        if switch.isChecked():
            # Enabled state - bright solid color
            bg_color = switch.active_color
            text_color = "white"  # White text for enabled state
        else:
            # Disabled state - muted/gray color
            bg_color = "#CCCCCC"  # Gray for disabled state
            text_color = "#666666"  # Dark gray text for disabled state
            
        # Apply dynamic styling for active/inactive state
        if switch.isChecked():
            switch.setStyleSheet(f"""
                QCheckBox {{
                    background: {switch.active_color};
                    color: white;
                }}
                QCheckBox:hover {{
                    background: {switch.active_color};
                }}
            """)
        else:
            # Reset to default stylesheet styling
            switch.setStyleSheet("")

    def on_switch_toggled(self, switch, checked):
        """Handle any toggle switch change."""
        # 1) Update state
        key = switch.state_key               # e.g. 'face_tracking', 'voice', 'ai_agent'
        self.button_states[key] = checked
        
        if key == 'voice':
            # main mic: self.voice_btn (toggle switch)
            # tiny mic: self.chat_voice_btn (simple button - may not exist before chat is shown)
            for other in (getattr(self, 'voice_btn', None), getattr(self, 'chat_voice_btn', None)):
                if other is None or other is switch:
                    continue
                other.blockSignals(True)
                other.setChecked(checked)
                # Only update switch style for the main voice button (toggle switch)
                if hasattr(other, 'state_key') and other != self.chat_voice_btn:
                    self.update_switch_style(other)
                other.blockSignals(False)

        # 2) Route to the right start/stop
        self._handle_toggle(key, checked)

        # 3) UI updates (once)
        self.update_switch_style(switch)
        self.update_status_bar()

        # 4) Log
        print(f"{switch.text()} {'activated' if checked else 'deactivated'}")
        active = [k.replace('_', ' ').title() for k, v in self.button_states.items() if v]
        print(f"Current active features: {active}")


    # ----------------- Toggle Dispatcher -----------------

    def _handle_toggle(self, key: str, state: bool):
        """Start/stop services based on toggle key."""
        print('dispatch', key)
        dispatch = {
            'face_tracking': (self._start_face_tracking, self._stop_face_tracking),
            'voice'        : (self._start_voice,         self._stop_voice),
            'ai_agent'     : (lambda: self.toggle_chat_interface(True),
                            lambda: self.toggle_chat_interface(False)),
        }

        start_fn, stop_fn = dispatch.get(key, (None, None))
        if not start_fn:
            print(f"[warn] Unknown toggle key: {key}")
            return

        if state:
            start_fn()
        else:
            stop_fn()


    # ----------------- Face Tracking -----------------

    def _start_face_tracking(self):
        if getattr(self, 'tracker', None) is None:
            self.tracker = HeadMouseTracker()
            self.tracker.start(block=False)  # non-blocking
            print("[face_tracking] started")

    def _stop_face_tracking(self):
        if getattr(self, 'tracker', None):
            try:
                self.tracker.stop()
            finally:
                self.tracker = None
            print("[face_tracking] stopped")


    # ----------------- Voice (Vosk) -----------------

    def _start_voice(self):
        """Start speech recognizer; also sync any UI mic state if you have one."""
        if getattr(self, 'recognizer', None) is None:
            self.is_recording = True
            self.recognizer = VoskMicRecognizer(model="language_models/eng_model", on_result=self.handle_voice_result)
            self.recognizer.start(background=True)
            print("[voice] started")

    def _stop_voice(self):
        if getattr(self, 'recognizer', None):
            try:
                self.recognizer.stop()
            finally:
                self.recognizer = None

        self.is_recording = False
        print("[voice] stopped")

    # --------------- Chat Gemini -----------------------------
    def _start_chat(self):
        self.chat = HaloChat()
        self.chat.start()
        print("[chat] started")

    def toggle_chat_interface(self, show_chat):
        """Show or hide the chat interface with animation"""
        # For full-height sidebar, we don't need to animate height changes
        # Just show/hide the chat widget
        self.chat_widget.setVisible(show_chat)
        
        if show_chat:
            self.chat_display.setPlainText("AI: Hello!\nHow can I help you today?")
        else:
            self.chat_display.clear()
    
    def update_status(self, message, color="#4682B4"):
        """Update the status label with heavenly styling"""
        self.status_label.setText(message)
        if color != "#4682B4":
            self.status_label.setStyleSheet(f"color: {color};")
        else:
            self.status_label.setStyleSheet("")
    
    def toggle_sidebar(self):
        """Toggle sidebar expansion/collapse"""
        if self.is_expanded:
            self.collapse_sidebar()
        else:
            self.expand_sidebar()
    
    def collapse_sidebar(self):
        """Collapse the entire window into circular HALO"""
        if not self.is_expanded:
            return
            
        self.is_expanded = False
        
        # Hide all content - only show the button
        self.content_widget.setVisible(False)
        
        # First change to frameless to remove window decorations
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Transform button to fill entire circular window
        self.toggle_btn.setFixedSize(80, 80)
        self.toggle_btn.setText("HALO")
        self.update_circular_halo_style()
        
        # Apply circular mask to make window truly circular
        self.apply_circular_mask()
        
        # Show the window again after changing flags
        self.show()
        
        # Set the geometry directly after becoming frameless
        screen = QApplication.primaryScreen().availableGeometry()
        new_x = screen.width() - 80  # 80px circle
        new_y = (screen.height() - 80) // 2  # Center vertically
        
        # Set size and position directly (no animation for collapse to avoid geometry issues)
        self.setFixedSize(80, 80)
        self.move(new_x, new_y)
    
    def expand_sidebar(self):
        """Expand the window from circular HALO to full panel"""
        if self.is_expanded:
            return
            
        self.is_expanded = True
        
        # Remove circular mask first
        self.clearMask()
        
        # Restore window frame (make it movable again)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # Show the window again after changing flags
        self.show()
        
        # Restore window to full panel size and position
        screen = QApplication.primaryScreen().availableGeometry()
        new_x = screen.width() - self.expanded_width
        self.setFixedSize(self.expanded_width, self.window_height)
        self.move(new_x, self.margin_top)
        
        # Show the main content
        self.content_widget.setVisible(True)
        
        # Transform button back to arrow
        self.toggle_btn.setFixedSize(35, 90)  # Original size
        self.toggle_btn.setText("◀")  # Left arrow when expanded
        self.toggle_btn.setStyleSheet("")  # Reset to stylesheet styling
        
        # Reload the main stylesheet to restore normal styling
        self.load_stylesheet()
    
    def enterEvent(self, event):
        """Mouse entered the widget"""
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Mouse left the widget"""
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            self.drag_position = None
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
        region = QRegion(0, 0, 80, 80, QRegion.Ellipse)
        self.setMask(region)
    
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
    # Create the application
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Vision & AI Assistant")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    window = CollapsibleSidebar()
    window.show()
    
    # Run the application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
