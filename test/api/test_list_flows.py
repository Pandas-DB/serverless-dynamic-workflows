# tools/flow/list_flows.py
# !/usr/bin/env python3
import json
import requests
import sys
from pathlib import Path
from tabulate import tabulate  # For pretty printing tables


token = os.getenv('TOKEN')
api_url_ = os.getenv('API_URL')


def list_flows(api_url=None, format='table'):
    """List all available flows"""
    # Get API URL if not provided
    if not api_url:
        api_url = api_url_

    # Prepare request
    headers = {
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json'
    }

    try:
        response = requests.get(
            f"{api_url}/flows",
            headers=headers
        )

        # Check for errors
        response.raise_for_status()
        flows = response.json().get('flows', [])

        if format == 'json':
            print(json.dumps(flows, indent=2))
        else:
            # Prepare table data
            table_data = []
            for flow in flows:
                table_data.append([
                    flow.get('name', 'N/A'),
                    flow.get('description', 'N/A'),
                    len(flow.get('definition', {}).get('States', {})),
                    flow.get('created', 'N/A')
                ])

            # Print table
            headers = ['Name', 'Description', 'States', 'Created']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            print(f"\nTotal flows: {len(flows)}")

        return flows

    except requests.exceptions.RequestException as e:
        print(f"Error listing flows: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='List all available flows')
    parser.add_argument('--api-url', help='API URL (optional, will be fetched from CloudFormation if not provided)')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format (default: table)')
    args = parser.parse_args()

    list_flows(args.api_url, args.format)


if __name__ == '__main__':
    main()