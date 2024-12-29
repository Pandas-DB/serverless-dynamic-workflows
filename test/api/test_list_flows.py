# tools/flow/list_flows.py
import os
import json
import requests
import sys
from pathlib import Path
from tabulate import tabulate
from urllib.parse import urljoin


def build_api_url(base_url, stage='dev'):
    """Builds the complete API URL with stage"""
    # Remove trailing slashes from base_url
    base_url = base_url.rstrip('/')
    # Add stage if not present in the URL
    if not base_url.endswith(f'/{stage}'):
        base_url = f"{base_url}/{stage}"
    return base_url


def list_flows(api_url=None, format='table', stage='dev'):
    """List all available flows"""
    token = os.getenv('TOKEN')
    api_url_ = os.getenv('API_URL')

    if not token:
        print("Error: TOKEN environment variable not set")
        sys.exit(1)

    if not api_url and not api_url_:
        print("Error: Either --api-url argument or API_URL environment variable must be set")
        sys.exit(1)

    # Get API URL and add stage if needed
    base_url = api_url or api_url_
    # full_url = build_api_url(base_url, stage)
    full_url = base_url

    # Prepare request
    headers = {
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json'
    }

    try:
        # Make request to the flows endpoint
        url = f"{full_url}/flows"
        print(f"Requesting: {url}")  # Debug information

        response = requests.get(
            url,
            headers=headers
        )

        # Print debug information for non-200 responses
        if response.status_code != 200:
            print(f"Status Code: {response.status_code}")
            print("Response Headers:", json.dumps(dict(response.headers), indent=2))
            print("Response Body:", response.text)
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
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print("Response Headers:", json.dumps(dict(e.response.headers), indent=2))
            print("Response Body:", e.response.text)
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='List all available flows')
    parser.add_argument('--api-url', help='API URL (optional, will use API_URL env var if not provided)')
    parser.add_argument('--stage', default='dev', help='API stage (default: dev)')
    parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format (default: table)')
    args = parser.parse_args()

    list_flows(args.api_url, args.format, args.stage)


if __name__ == '__main__':
    main()