"""HALO Chat - AI assistant using Google Gemini"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

class HaloChat:
    """AI chat interface using Google Gemini"""
    
    def __init__(self, api_key=None, model="gemini-1.5-flash", temp=0.0):
        # Load API key
        load_dotenv()
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or "AIzaSyChOPtzyr_Ypy9dBUG0Q-nBWwjvSPB6lt8"
        genai.configure(api_key=self.api_key)
        
        # Model settings
        self.model = model
        self.temp = temp
        self.chat = None

    def start(self):
        """Initialize the chat session"""
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=(
                "You are HALO, a helpful AI assistant. "
                "Help users with computer tasks and accessibility. "
                "Keep responses concise and practical. "
                "When generating text to copy, prefix with 'Copy below:'"
                "Do not add any decotative symbols such as # or >"
                "Please autofill information do not put in [insert here]"
            ),
            generation_config=genai.GenerationConfig(
                temperature=self.temp,
                max_output_tokens=200,
                top_p=0.8,
                top_k=40,
            ),
        )
        self.chat = model.start_chat(enable_automatic_function_calling=True)
        print("HALO chat initialized")

    def generate_response(self, question, history=None):
        """Generate response to user question"""
        if not self.chat:
            raise RuntimeError("Chat not started. Call start() first.")
        response = self.chat.send_message(question)
        return response.text

    def stop(self):
        """Stop the chat session"""
        self.chat = None
        print("Chat stopped")
