from config import API_KEY
import requests
from mistralai import Mistral

client = Mistral(api_key=API_KEY)
model = "open-mistral-nemo"

chat_response = client.chat.complete(
    model= model,
    messages = [
        {
            "role": "user",
            "content": "What is the best French cheese?",
        },
    ]
)
print(chat_response.choices[0].message.content)