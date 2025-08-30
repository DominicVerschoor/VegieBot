# VegieBot Workflow Documentation

## Project Overview
VegieBot is an AI-powered assistant application with a modern GUI interface that provides:
- Face tracking for mouse control
- Voice recognition and commands
- AI chat assistant integration
- Accessibility features (colorblind mode)

## Setup and Installation

### Prerequisites
- Python 3.8 or higher
- Webcam (for face tracking)
- Microphone (for voice commands)

### Installation Steps
1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Download Vosk language model:
   - Create `language_models/` directory
   - Download English model from Vosk website
   - Extract to `language_models/eng_model/`

### Environment Configuration
Create a `.env` file in the project root with your API keys:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

## Application Architecture

### Main Components
- **App.py**: Main GUI application and window management
- **MonitorTracking.py**: Head/face tracking for cursor control
- **VoiceControl.py**: Voice recognition and command processing
- **Chatbot.py**: AI chat integration with Google Gemini
- **CursorCircle.py**: Visual cursor indicators

### Key Features

#### 1. Face Tracking
- Uses MediaPipe for real-time face detection
- Converts head movements to mouse cursor control
- Toggle on/off via GUI switch

#### 2. Voice Commands
- Continuous voice recognition using Vosk
- Mouse command support:
  - "click" or "left click" - Left mouse click
  - "right click" - Right mouse click
  - "middle click" - Middle mouse click
  - "shift click" - Shift + left click
- Voice-to-text for chat input

#### 3. AI Assistant
- Integration with Google Gemini AI
- Chat interface within the GUI
- Voice input support for conversations

#### 4. GUI Interface
- Collapsible sidebar design
- Draggable window when collapsed to circular "HALO" button
- Status indicators for active features
- Modern styling with external CSS (styles.qss)

## Usage Workflow

### Starting the Application
```bash
python App.py
```

### Basic Operations
1. **Enable Face Tracking**: Toggle the "Face Tracking" switch
2. **Enable Voice Commands**: Toggle the "Voice Detection" switch
3. **Access AI Assistant**: Toggle the "AI Agent" switch to show chat interface
4. **Collapse Interface**: Click the arrow button to minimize to circular HALO

### Voice Commands
- Say "click" to perform a left mouse click
- Say "right click" for right mouse button
- Say "middle click" for middle mouse button
- Speak naturally for AI chat when voice input is active

### Chat Interface
- Type messages directly or use voice input
- Click microphone button to toggle voice recording
- Press Enter to send messages
- AI responses appear in the chat display area

## Development Workflow

### Code Structure
```
VegieBot/
├── App.py              # Main application
├── MonitorTracking.py  # Face tracking module
├── VoiceControl.py     # Voice recognition module
├── Chatbot.py          # AI chat integration
├── CursorCircle.py     # Cursor visual effects
├── styles.qss          # GUI styling
├── requirements.txt    # Dependencies
├── .env               # Environment variables
└── language_models/   # Vosk models directory
```

### Adding New Features
1. Import required modules in relevant component files
2. Update GUI elements in App.py if needed
3. Add styling to styles.qss for new UI elements
4. Update requirements.txt if new dependencies are added
5. Test all functionality before committing

### Testing Checklist
- [ ] GUI loads without errors
- [ ] Face tracking activates webcam and moves cursor
- [ ] Voice commands trigger mouse actions
- [ ] Chat interface sends/receives messages
- [ ] Window dragging works in both expanded/collapsed states
- [ ] All toggle switches function correctly
- [ ] External styling loads properly

## Troubleshooting

### Common Issues
1. **ImportError for pyautogui**: Install with `pip install pyautogui`
2. **Webcam not detected**: Check camera permissions and availability
3. **Voice recognition not working**: Verify microphone permissions and Vosk model installation
4. **AI chat errors**: Check Google API key configuration in .env file
5. **Styling issues**: Ensure styles.qss file exists in project directory

### Performance Optimization
- Face tracking uses threading for non-blocking operation
- Voice recognition runs in background threads
- GUI updates use Qt signals for thread safety
- Resource cleanup on application exit

## API Integration

### Google Gemini API
- Configure API key in environment variables
- Handle rate limiting and error responses
- Maintain conversation context in chat sessions

### Voice Recognition (Vosk)
- Supports offline speech recognition
- Requires model download for target language
- Real-time processing with configurable thresholds

## Security Considerations
- Keep API keys in environment variables, never in code
- Validate all user inputs before processing
- Handle microphone/camera permissions appropriately
- Sanitize file paths and system commands