# test/api/test_api_usage.py
import os
import requests
import json

token = os.getenv('TOKEN')
api_url = os.getenv('API_URL')
user_id = os.getenv('USER_ID')

headers = {
    'Authorization': f"Bearer {token}",
    'Content-Type': 'application/json'
}

# Get usage for a specific user
response = requests.get(
    f'{api_url}/usage/{user_id}',
    headers=headers
)

print("API Usage Response:")
print(json.dumps(response.json(), indent=2))

# Optional: Get usage with date range
response_with_dates = requests.get(
    f'{api_url}/usage/{user_id}?startDate=2024-01&endDate=2024-12',
    headers=headers
)

print("\nAPI Usage with date range:")
print(json.dumps(response_with_dates.json(), indent=2))