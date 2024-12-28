import os
import requests
import time
import urllib.parse


def get_flow_result(flow_name, execution_arn, max_wait=300):
    start_time = time.time()
    encoded_arn = urllib.parse.quote(execution_arn)

    while time.time() - start_time < max_wait:
        response = requests.get(
            f'{api_url}/run/{flow_name}/{encoded_arn}',
            headers=headers
        )
        result = response.json()

        if result['status'] in ['SUCCEEDED', 'FAILED']:
            return result

        time.sleep(2)

    raise TimeoutError(f"Execution timeout after {max_wait}s")


# Setup credentials and API URL
token = os.getenv('TOKEN')
api_url = os.getenv('API_URL')

headers = {
    'Authorization': f"Bearer {token}",
    'Content-Type': 'application/json'
}

# Start the composite flow execution
response = requests.post(
    f'{api_url}/run/compositeFlow',
    headers=headers,
    json={
        "message": "Testing composite flow"
    }
)
print("Initial response:", response.json())
assert response.json()['status'] == 'SUCCESS'

# Get and monitor the main flow execution
main_execution_arn = response.json()['executionArn']
result = get_flow_result('compositeFlow', main_execution_arn)
print("\nFinal composite flow result:", result)
assert result['status'] == 'SUCCEEDED'

# If you want to see the results of individual flows, they will be in the output
if result.get('output'):
    try:
        # The parallel state results will be in an array
        parallel_results = result['output'][0]  # Results from ParallelFlows
        print("\nParallel Flow Results:")
        print("Flow1 Result:", parallel_results[0])
        print("Flow2 Result:", parallel_results[1])

        # Flow3 result will be the second item in the main output
        print("\nFlow3 Result:", result['output'][1])
    except (KeyError, IndexError) as e:
        print("Error parsing flow results:", e)