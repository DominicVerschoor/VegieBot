import json

def get_relevant_info(user_question: str):
    """Identifies and retrieves the unique identifiers of all the tables that are relevant to a given user question.
    Relevance is determined by analyzing the content and metadata of tables in the dataset to align with the intent and context of the user's question.
    Each of the returned tables is a potential source of information to answer the user's query and should be further analyzed to extract relevant data.

    Args:
        user_question: The user's question or query, which will be analyzed to determine relevant tables from the dataset.
    """
    
    api_response = 'function called'
    return api_response

functions = {
    "get_relevant_tables": get_relevant_info,
}

def process_query_with_function_calls(chat, user_question):
    response = chat.send_message(user_question)
    return response.text
