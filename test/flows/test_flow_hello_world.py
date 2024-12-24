import os
import requests

token = os.getenv('TOKEN')
api_url = os.getenv('API_URL')

headers = {
    'Authorization': f"Bearer {token}",
    'Content-Type': 'application/json'
}

response = requests.post(
    f'{api_url}/run/helloWorldFlow',
    headers=headers,
    json={}
)
print(response.json())
