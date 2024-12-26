import os
import requests
import time
import urllib.parse


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


def get_flow_result(execution_arn, max_wait=300):
    start_time = time.time()
    # After getting the execution ARN from the POST response
    encoded_arn = urllib.parse.quote(execution_arn)
    while time.time() - start_time < max_wait:
        response = requests.get(
            f'{api_url}/run/helloWorldFlow/{encoded_arn}',
            headers=headers
        )
        result = response.json()

        if result['status'] in ['SUCCEEDED', 'FAILED']:
            return result

        time.sleep(2)

    raise TimeoutError(f"Execution timeout after {max_wait}s")


# Use it
execution_arn = response.json()['executionArn']
result = get_flow_result(execution_arn)
print(result)
