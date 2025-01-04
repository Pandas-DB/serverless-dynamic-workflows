# tools/flow/list_runs.py
import os
import json
import requests
import sys
from pathlib import Path
from tabulate import tabulate
from typing import List, Dict, Optional, Union


def build_api_url(base_url: str) -> str:
    """
    Builds the complete API URL with stage

    Args:
        base_url: Base API Gateway URL
        stage: API stage (default: dev)

    Returns:
        str: Complete API URL
    """
    # Remove trailing slashes and ensure https:// is present
    base_url = base_url.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"

    return base_url


def list_runs(api_url: Optional[str] = None, output_format: str = 'table', stage: str = 'dev') -> List[Dict]:
    """
    List all flow executions for the authenticated user

    Args:
        api_url: Optional API URL override
        output_format: Output format ('table' or 'json')
        stage: API stage (default: dev)

    Returns:
        List[Dict]: List of executions
    """
    # Validate environment and arguments
    token = os.getenv('TOKEN')
    api_url_ = os.getenv('API_URL')

    if not token:
        print("Error: TOKEN environment variable not set")
        sys.exit(1)

    if not api_url and not api_url_:
        print("Error: Either --api-url argument or API_URL environment variable must be set")
        sys.exit(1)

    # Build complete API URL
    base_url = api_url or api_url_
    full_url = build_api_url(base_url)
    url = f"{full_url}/runs"

    headers = {
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json'
    }

    try:
        print(f"Requesting: {url}")
        response = requests.get(
            url,
            headers=headers,
        )

        # Handle non-200 responses with detailed error information
        if response.status_code != 200:
            print(f"Status Code: {response.status_code}")
            print("Response Headers:", json.dumps(dict(response.headers), indent=2))
            print("Response Body:", response.text)
            response.raise_for_status()

        # Parse response data
        data = response.json()
        executions = data.get('executions', [])

        # Output handling
        if output_format == 'json':
            print(json.dumps(data, indent=2))
        else:
            table_data = []
            for execution in executions:
                # Format status with symbols
                status = execution.get('status', 'N/A')
                status_display = {
                    'SUCCEEDED': f"✓ {status}",
                    'FAILED': f"✗ {status}",
                    'RUNNING': f"⋯ {status}",
                    'TIMED_OUT': f"⏰ {status}",
                    'ABORTED': f"⊘ {status}"
                }.get(status, status)

                # Build table row
                table_data.append([
                    execution.get('flowName', 'N/A'),
                    status_display,
                    execution.get('startDate', 'N/A'),
                    execution.get('stopDate', 'N/A'),
                    execution.get('name', 'N/A')
                ])

            # Print formatted table
            headers = ['Flow', 'Status', 'Start Date', 'Stop Date', 'Execution ID']
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
            print(f"\nTotal executions: {data.get('count', 0)}")

        return executions

    except requests.exceptions.RequestException as e:
        print(f"Error listing executions: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status Code: {e.response.status_code}")
            print("Response Headers:", json.dumps(dict(e.response.headers), indent=2))
            print("Response Body:", e.response.text)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)


def main():
    """Command line interface for listing executions"""
    import argparse

    parser = argparse.ArgumentParser(
        description='List all flow executions for the authenticated user',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        '--api-url',
        help='API URL (optional, will use API_URL env var if not provided)'
    )
    parser.add_argument(
        '--stage',
        default='dev',
        help='API stage'
    )
    parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format'
    )

    args = parser.parse_args()
    list_runs(args.api_url, args.format, args.stage)


if __name__ == '__main__':
    main()