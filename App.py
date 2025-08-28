import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QLabel, QFrame, QHBoxLayout, QTextEdit, 
                               QLineEdit, QScrollArea, QSizePolicy, QCheckBox)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, QRect
from PySide6.QtGui import QFont, QPalette, QColor
import json

from MonitorTracking import HeadMouseTracker
from VoiceControl import VoskMicRecognizer
from Chatbot import HaloChat

class CollapsibleSidebar(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vision & AI Control Panel")
        self.expanded_width = 320
        self.collapsed_width = 30
        
        # Get screen dimensions for full height coverage
        screen = QApplication.primaryScreen().availableGeometry()
        self.base_height = screen.height()
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
        
        # Set window properties
        self.setFixedSize(self.expanded_width, self.window_height)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # Position window to cover entire right edge of screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.expanded_width, 0)
        
        # Set up the main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Create main horizontal layout
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create heavenly toggle button
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setFixedSize(35, 90)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background: #87CEEB;
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.6);
                font-size: 20px;
                font-weight: bold;
                border-top-left-radius: 15px;
                border-bottom-left-radius: 15px;
            }
            QPushButton:hover {
                background: #4682B4;
                border: 2px solid rgba(255, 255, 255, 0.9);
            }
        """)
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
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title_label.setStyleSheet("""
            color: #4682B4;
            text-shadow: 2px 2px 4px rgba(255, 255, 255, 0.8);
        """)
        
        # Add heavenly close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: #FF69B4;
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.7);
                border-radius: 15px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FF1493;
                border: 2px solid rgba(255, 255, 255, 1.0);
            }
        """)
        self.close_btn.clicked.connect(self.close_application)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        
        # Heavenly status bar
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setStyleSheet("""
            QLabel {
                background: rgba(173, 216, 230, 0.3);
                border: 2px solid rgba(176, 224, 230, 0.8);
                border-radius: 10px;
                padding: 10px;
                color: #4682B4;
                font-size: 12px;
                font-weight: bold;
                margin-top: 8px;
            }
        """)
        self.update_status_bar()
        
        top_layout.addLayout(header_layout)
        top_layout.addWidget(self.status_label)
        
        layout.addWidget(top_section)
        
        # Add heavenly separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("""
            QFrame {
                color: rgba(135, 206, 235, 0.6);
                background: rgba(135, 206, 235, 0.8);
                border: none;
                height: 2px;
                margin: 10px 20px;
            }
        """)
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
        
        # Set up hover timer for auto-expand
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.expand_sidebar)
        
        # Initially expanded
        self.is_expanded = True
        
        # Set application stylesheet with solid white background
        self.setStyleSheet("""
            QMainWindow {
                background: white;
                border: 3px solid rgba(255, 255, 255, 0.8);
                border-radius: 20px;
            }
        """)
        
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
        chat_container.setFixedHeight(self.chat_height)
        chat_container.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.95);
                border: 3px solid rgba(135, 206, 235, 0.8);
                border-radius: 15px;
                margin: 8px;
            }
        """)
        
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(8)
        
        # Heavenly chat header
        chat_header = QLabel(" AI Assistant ")
        chat_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        chat_header.setStyleSheet("""
            color: #4682B4; 
            margin-bottom: 8px; 
            border: none;
            text-shadow: 1px 1px 3px rgba(255, 255, 255, 0.8);
        """)
        chat_layout.addWidget(chat_header)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(60)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 2px solid rgba(176, 224, 230, 0.6);
                border-radius: 10px;
                padding: 8px;
                font-size: 13px;
                color: black;
                font-family: 'Segoe UI';
            }
        """)
        self.chat_display.setPlaceholderText("AI responses will appear here...")
        chat_layout.addWidget(self.chat_display)
        
        # Input area - separate rows for text input and buttons
        # First row: text input (larger)
        self.chat_input = QTextEdit()
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.setStyleSheet("""
            QTextEdit {
                background: #FFFFFF;
                border: 2px solid #87CEEB;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
                color: #000000;
                font-family: Arial, sans-serif;
                font-weight: normal;
            }
            QTextEdit:focus {
                border-color: #4682B4;
                background: #FFFFFF;
            }
        """)
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
        self.chat_voice_btn.setFixedSize(70, 70)
        self.chat_voice_btn.setCheckable(True)
        self.chat_voice_btn.setToolTip("Voice input")
        self.chat_voice_btn.setStyleSheet("""
            QPushButton {
                background: #F0E68C;
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.7);
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:checked {
                background: #DAA520;
                border: 2px solid rgba(255, 255, 255, 0.9);
            }
            QPushButton:hover {
                background: #DAA520;
                border: 2px solid rgba(255, 255, 255, 1.0);
            }
        """)

        
        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(100)
        send_btn.setStyleSheet("""
            QPushButton {
                background: #87CEEB;
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.7);
                border-radius: 10px;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: bold;
                font-family: 'Segoe UI';
                text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
                min-height: 20px;
            }
            QPushButton:hover {
                background: #4682B4;
                border: 2px solid rgba(255, 255, 255, 1.0);
            }
            QPushButton:pressed {
                background: #4169E1;
            }
        """)
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
            self.chat_input.setStyleSheet("""
                QTextEdit {
                    background: #FFFACD;
                    border: 3px solid #FFD700;
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 13px;
                    color: black;
                    font-family: 'Segoe UI';
                }
            """)
            print("Voice recording started...")
            
        else:
            # Stop recording
            self.is_recording = False
            self.chat_input.setPlaceholderText("Type your message here...")
            self.chat_input.setStyleSheet("""
                QTextEdit {
                    background: white;
                    border: 2px solid rgba(135, 206, 235, 0.5);
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 13px;
                    color: black;
                    font-family: 'Segoe UI';
                }
                QTextEdit:focus {
                    border-color: #87CEEB;
                    background: white;
                }
            """)
            
            print("Voice recording stopped. Transcribed text added to input.")

    def handle_voice_result(self, result_json: str):
        text = f'{json.loads(result_json).get("text", "")}. '
        current_text = self.chat_input.toPlainText()
        self.chat_input.setPlainText(current_text + text)       

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
            
        switch.setStyleSheet(f"""
            QCheckBox {{
                background: {bg_color};
                color: {text_color};
                border: 2px solid rgba(255, 255, 255, 0.8);
                border-radius: 15px;
                padding: 18px;
                font-size: 15px;
                font-weight: bold;
                letter-spacing: 1px;
                min-height: 25px;
            }}
            QCheckBox:hover {{
                background: {switch.active_color if switch.isChecked() else '#DDDDDD'};
                border: 3px solid rgba(255, 255, 255, 1.0);
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 10px;
                border: 2px solid white;
                background: {'#2E8B57' if switch.isChecked() else '#CCCCCC'};
                margin-right: 8px;
            }}
            QCheckBox::indicator:checked {{
                background: #2E8B57;
            }}
            QCheckBox::indicator:unchecked {{
                background: #CCCCCC;
            }}
        """)

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
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background: rgba(173, 216, 230, 0.3);
                border: 2px solid rgba(176, 224, 230, 0.8);
                border-radius: 10px;
                padding: 10px;
                color: {color};
                font-size: 12px;
                font-weight: bold;
            }}
        """)
    
    def toggle_sidebar(self):
        """Toggle sidebar expansion/collapse"""
        if self.is_expanded:
            self.collapse_sidebar()
        else:
            self.expand_sidebar()
    
    def collapse_sidebar(self):
        """Collapse the sidebar"""
        if not self.is_expanded:
            return
            
        self.is_expanded = False
        self.toggle_btn.setText("▶")
        
        # Get current position
        current_rect = self.geometry()
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Calculate new position (move further right to hide content)
        new_x = screen.width() - self.collapsed_width
        new_rect = QRect(new_x, 0, self.collapsed_width, screen.height())
        
        # Animate the collapse
        self.sidebar_animation.setStartValue(current_rect)
        self.sidebar_animation.setEndValue(new_rect)
        self.sidebar_animation.start()
    
    def expand_sidebar(self):
        """Expand the sidebar"""
        if self.is_expanded:
            return
            
        self.is_expanded = True
        self.toggle_btn.setText("◀")
        
        # Get current position
        current_rect = self.geometry()
        screen = QApplication.primaryScreen().availableGeometry()
        
        # Calculate new position
        new_x = screen.width() - self.expanded_width
        new_rect = QRect(new_x, 0, self.expanded_width, screen.height())
        
        # Animate the expansion
        self.sidebar_animation.setStartValue(current_rect)
        self.sidebar_animation.setEndValue(new_rect)
        self.sidebar_animation.start()
    
    def enterEvent(self, event):
        """Mouse entered the widget"""
        if not self.is_expanded:
            self.hover_timer.start(300)  # 300ms delay before expanding
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Mouse left the widget"""
        self.hover_timer.stop()
        super().leaveEvent(event)

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
