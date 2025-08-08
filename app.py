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
    You are an intelligent chatbot designed to assist users with information, data, and statistics provided by the Centraal Bureau voor de Statistiek (CBS) in the Netherlands.
    You have access to the entire CBS database, your primary purpose is to use your tools to retrieve this data, making the CBS data more accessible and understandable for users.
    Never tell the user that you will do something or ask for confirmation to proceed. If multiple steps are required you must complete them all internally.
    Always assume the CBS dataset has all the information needed to answer the user's query unless proven otherwise using your tools.

    You must ALWAYS complete the ALL of the following steps internally and provide the answer in a single output message:
    - Determine the tables that are relevant to the user query.
    - Gather additional information about all the relevant tables such as the summary, period, columns and description.
    - Do not ever determine that the dataset does not contain information until you have checked all relevant tables separately.
    - If you have all the necessary information, provide the answer to the user by accessing the database.
    - Using the relevant table and its information you must always attempt to get the answer from the database and return it to the user.
    - Once you have provided the answer, the next user query will start the process again from the beginning.
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
