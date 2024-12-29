import json
import boto3
import logging
from typing import Dict, Any
import traceback

from functions.base.api_usage.handler import track_usage_middleware

# Enhanced logging setup
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Add timestamp and request id to log format
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] RequestId: %(aws_request_id)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

sfn = boto3.client('stepfunctions')


@track_usage_middleware
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handles the API Gateway event to list all available Step Function workflows.
    """
    try:
        logger.info(f"Received event: {json.dumps(event, indent=2)}")

        # List all state machines
        paginator = sfn.get_paginator('list_state_machines')
        flows = []

        for page in paginator.paginate():
            for state_machine in page['stateMachines']:
                # Get detailed info for each state machine
                details = sfn.describe_state_machine(
                    stateMachineArn=state_machine['stateMachineArn']
                )

                # Extract flow information
                flow = {
                    'name': state_machine['name'],
                    'created': state_machine['creationDate'].isoformat(),
                    'definition': json.loads(details['definition']),
                    'description': details.get('description', 'No description available')
                }
                flows.append(flow)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'flows': flows,
                'count': len(flows)
            })
        }

    except Exception as e:
        error_msg = f"Error listing flows: {str(e)}"
        logger.error(error_msg)
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'details': str(e)
            })
        }