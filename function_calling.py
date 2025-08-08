import json

def get_name(user_question: str):
    """This function woill return your name. Use this to tell users your name.

    Args:
        user_question: The user's question
    """
    
    api_response = 'VEGIEBOT'
    return api_response

functions = {
    "get_name": get_name,
}

def process_query_with_function_calls(chat, user_question):
    response = chat.send_message(user_question)
    return response.text
