# tools/flow/test_flow.py
# !/usr/bin/env python3

import json
import argparse
import requests
import time
import sys
from pathlib import Path

token = os.getenv('TOKEN')
api_url_ = os.getenv('API_URL')


def execute_flow(flow_name, input_data=None, api_url=None):
    """Execute a flow and return the result"""
    # Get API URL if not provided
    if not api_url:
        api_url = api_url_

    # Prepare request
    headers = {
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json'
    }

    # Default input data if none provided
    if input_data is None:
        input_data = {"test": True}

    # Make request
    try:
        response = requests.post(
            f"{api_url}/run/{flow_name}",
            headers=headers,
            json=input_data
        )

        # Check for errors
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error executing flow: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Test a flow execution')
    parser.add_argument('--flow', default='dummy2StepFlow', help='Name of the flow to execute')
    parser.add_argument('--input', help='JSON input data for the flow')
    parser.add_argument('--api-url', help='API URL (optional, will be fetched from CloudFormation if not provided)')
    args = parser.parse_args()

    # Parse input data if provided
    input_data = None
    if args.input:
        try:
            input_data = json.loads(args.input)
        except json.JSONDecodeError:
            print("Error: Input data must be valid JSON")
            sys.exit(1)

    print(f"\nExecuting flow: {args.flow}")
    print(f"Input data: {input_data or 'default'}")
    print("---------------------------")

    # Execute flow and print result
    result = execute_flow(args.flow, input_data, args.api_url)
    print("\nFlow execution result:")
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()