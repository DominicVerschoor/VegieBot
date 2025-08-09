import requests

resp = requests.post(
    "http://127.0.0.1:5000/chat",  # Changed from "/" to "/chat"
    json={"message": "hi what is your name?"}
)

# Only call .json() if the response is successful
if resp.status_code == 200:
    print(resp.json())
else:
    print("Error occurred, response is not JSON")