import os
import json
import random
import google.generativeai as genai
from dotenv import load_dotenv

class HaloChat:
    def __init__(self, api_key="AIzaSyChOPtzyr_Ypy9dBUG0Q-nBWwjvSPB6lt8", model_name="gemini-1.5-flash", temperature=0.0):
        # Load API key from .env if not provided
        load_dotenv()
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=self.api_key)

        # Store model config
        self.model_name = model_name
        self.temperature = temperature
        self.chat = None

    def start(self):
        """Initialize the chat session in foreground."""
        function_calling_model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=(
                "You are a helpful chatbot named HALO. "
                "Your purpose is to help people with disabilities use the computer easier "
                "and answer general questions about computer usage for those who are not well versed in tech."
            ),
            generation_config=genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=200,
                top_p=0.8,
                top_k=40,
            ),
        )
        self.chat = function_calling_model.start_chat(
            enable_automatic_function_calling=True
        )
        print("[chat] HALO is ready.")

    def generate_response(self, user_question, history=None):
        """Send a message to the chat model and get the response text."""
        if not self.chat:
            raise RuntimeError("Chat session not started. Call start() first.")
        response = self.chat.send_message(user_question)
        return response.text

    def stop(self):
        """Stop the chat session."""
        self.chat = None
        print("[chat] stopped")
