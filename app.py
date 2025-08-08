import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Import your function calling logic
from function_calling import functions, process_query_with_function_calls

# --------------------
# Initialization
# --------------------
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not set in environment variables.")

genai.configure(api_key=google_api_key)

# Create Gemini model with your existing config
function_calling_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="""
    You are a simple chatbot designed to help people. If you use a function call, be sure the tell the user the name of the function you have used.
    """,
    tools=functions.values(),
    generation_config=genai.GenerationConfig(temperature=0.0),
)

# Start a chat session with auto function calling enabled
chat = function_calling_model.start_chat(enable_automatic_function_calling=True)

# --------------------
# Flask app setup
# --------------------
app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat_endpoint():
    """
    Expects JSON:
    {
        "message": "User question here"
    }
    """
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = data["message"]
    try:
        answer = process_query_with_function_calls(chat, user_message)
        return jsonify({"reply": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "Gemini function-calling API is running."})

# --------------------
# Run locally
# --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
