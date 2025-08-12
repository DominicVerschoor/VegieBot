import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QPushButton, QLabel, QFrame, QHBoxLayout, QTextEdit, 
                               QLineEdit, QScrollArea, QSizePolicy)
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
        
        # Button states with their colors
        self.button_states = {
            'face_tracking': False,
            'colorblind': False,
            'ai_agent': False
        }
        
        self.button_colors = {
            'face_tracking': '#3498db',
            'colorblind': '#e74c3c',
            'ai_agent': '#2ecc71'
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
        
        # Create toggle button (arrow) - positioned in middle of screen height
        self.toggle_btn = QPushButton("◀")
        self.toggle_btn.setFixedSize(30, 80)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                font-size: 18px;
                font-weight: bold;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
            }
            QPushButton:hover {
                background-color: #2c3e50;
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
        
        # Add title
        title_label = QLabel("Vision & AI")
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setStyleSheet("color: #2c3e50;")
        
        # Add close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(25, 25)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.close_btn.clicked.connect(self.close_application)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        
        # Status bar
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignLeft)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 8px;
                color: #7f8c8d;
                font-size: 11px;
                margin-top: 5px;
            }
        """)
        self.update_status_bar()
        
        top_layout.addLayout(header_layout)
        top_layout.addWidget(self.status_label)
        
        layout.addWidget(top_section)
        
        # Add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #bdc3c7;")
        layout.addWidget(separator)
        
        # Add stretch to center the buttons vertically
        layout.addStretch()
        
        # Create buttons
        self.face_tracking_btn = self.create_toggle_button(
            "Face Tracking", 
            "#3498db", 
            "#2980b9",
            "🎯",
            'face_tracking'
        )
        self.colorblind_btn = self.create_toggle_button(
            "Colorblind Mode", 
            "#e74c3c", 
            "#c0392b",
            "👁️",
            'colorblind'
        )
        self.ai_agent_btn = self.create_toggle_button(
            "AI Agent", 
            "#2ecc71", 
            "#27ae60",
            "🤖",
            'ai_agent'
        )
        self.voice_btn = self.create_toggle_button(
            "Voice Detection", 
            "#f39c12",  # Orange for normal
            "#e67e22",  # Darker orange for active
            "🎤",      # Microphone emoji
            'voice'
        )
        # Add voice button state and color to button_states and button_colors
        self.button_states['voice'] = False
        self.button_colors['voice'] = '#f39c12'
        
        # Add buttons to layout
        layout.addWidget(self.face_tracking_btn)
        layout.addWidget(self.colorblind_btn)
        layout.addWidget(self.ai_agent_btn)
        layout.addWidget(self.voice_btn)

        # Add stretch to center the buttons vertically
        layout.addStretch()
        
        # Create chat interface (initially hidden)
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
        
        # Set application stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
                border: 2px solid #bdc3c7;
                border-radius: 10px;
            }
        """)
        
        self._start_chat()
        
        # Enable mouse tracking for hover detection
        self.setMouseTracking(True)
        self.toggle_btn.setMouseTracking(True)
    
    def create_toggle_button(self, text, color, active_color, emoji, state_key):
        """Create a toggle button that can be activated/deactivated"""
        btn = QPushButton(f"{emoji}  {text}")
        btn.setMinimumHeight(50)
        btn.setFont(QFont("Arial", 11, QFont.Bold))
        btn.setCheckable(True)  # Make button toggleable
        
        # Store the colors and state key
        btn.normal_color = color
        btn.active_color = active_color
        btn.state_key = state_key
        
        self.update_button_style(btn)
        btn.clicked.connect(lambda: self.on_button_toggled(btn))
        
        return btn
    
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
                background-color: #ffffff;
                border: 2px solid #2ecc71;
                border-radius: 8px;
                margin: 5px;
            }
        """)
        
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        chat_layout.setSpacing(8)
        
        # Chat header
        chat_header = QLabel("🤖 AI Assistant")
        chat_header.setFont(QFont("Arial", 12, QFont.Bold))
        chat_header.setStyleSheet("color: #2ecc71; margin-bottom: 5px; border: none;")
        chat_layout.addWidget(chat_header)
        
        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setMaximumHeight(180)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                color: #495057;
            }
        """)
        self.chat_display.setPlaceholderText("AI responses will appear here...")
        chat_layout.addWidget(self.chat_display)
        
        # Input area with voice button
        input_layout = QHBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: #ffffff;
                border: 2px solid #dee2e6;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                color: #212529;
            }
            QLineEdit:focus {
                border-color: #2ecc71;
                background-color: #ffffff;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_message)
        
        self.chat_voice_btn = self.create_toggle_button(
            "🎤",
            "#f39c12",  # Orange for normal
            "#e67e22",  # Darker orange for active
            "",         # (emoji already in text)
            'voice'     # <-- same state_key as the main mic
        )
        self.chat_voice_btn.setFixedSize(35, 35)
        self.chat_voice_btn.setToolTip("Voice input")
        self.chat_voice_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #5a6268; }
            QPushButton:pressed { background-color: #e74c3c; }
        """)

        
        send_btn = QPushButton("Send")
        send_btn.setFixedWidth(60)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        send_btn.clicked.connect(self.send_message)
        
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(self.chat_voice_btn)
        input_layout.addWidget(send_btn)
        chat_layout.addLayout(input_layout)
        
        self.chat_voice_btn.clicked.connect(self.toggle_voice_input)
        
        return chat_container
    
    def toggle_voice_input(self):
        """Toggle voice input recording"""
        if self.is_recording:
            # Start recording
            self.is_recording = True
            self.chat_input.setPlaceholderText("🎤 Listening... (Click mic again to stop)")
            self.chat_input.setStyleSheet("""
                QLineEdit {
                    background-color: #fff3cd;
                    border: 2px solid #ffc107;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 11px;
                    color: #212529;
                }
            """)
            print("Voice recording started...")
            
        else:
            # Stop recording
            self.is_recording = False
            self.chat_input.setPlaceholderText("Type your message here...")
            self.chat_input.setStyleSheet("""
                QLineEdit {
                    background-color: #ffffff;
                    border: 2px solid #dee2e6;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 11px;
                    color: #212529;
                }
                QLineEdit:focus {
                    border-color: #2ecc71;
                    background-color: #ffffff;
                }
            """)
            
            print("Voice recording stopped. Transcribed text added to input.")

    def handle_voice_result(self, result_json: str):
        text = f'{json.loads(result_json).get("text", "")}. '
        text = self.chat_input.text() + text
        self.chat_input.setText(text)       

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
        message = self.chat_input.text().strip()
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

    def update_button_style(self, btn):
        """Update button style based on its checked state"""
        if btn.isChecked():
            bg_color = btn.active_color
            border_style = "border: 2px solid #ffffff;"
        else:
            bg_color = btn.normal_color
            border_style = "border: none;"
            
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: white;
                {border_style}
                border-radius: 8px;
                padding: 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn.active_color};
            }}
        """)

    def on_button_toggled(self, btn):
        """Handle any toggle button click."""
        # 1) Update state
        key = btn.state_key               # e.g. 'face_tracking', 'voice', 'ai_agent'
        state = btn.isChecked()
        self.button_states[key] = state
        
        if key == 'voice':
            # main mic: self.voice_btn
            # tiny mic: self.chat_voice_btn (may not exist before chat is shown)
            for other in (getattr(self, 'voice_btn', None), getattr(self, 'chat_voice_btn', None)):
                if other is None or other is btn:
                    continue
                other.blockSignals(True)
                other.setChecked(state)
                self.update_button_style(other)
                other.blockSignals(False)

        # 2) Route to the right start/stop
        self._handle_toggle(key, state)

        # 3) UI updates (once)
        self.update_button_style(btn)
        self.update_status_bar()

        # 4) Log
        print(f"{btn.text()} {'activated' if state else 'deactivated'}")
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
            self.chat_display.setPlainText("AI: Hello! I'm your AI assistant. How can I help you today?")
        else:
            self.chat_display.clear()
    
    def update_status(self, message, color="#7f8c8d"):
        """Update the status label with a message and color"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                padding: 6px;
                color: {color};
                font-size: 10px;
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
