# functions/base/run_flow/handler.py
import json
import boto3
import logging
from typing import Dict, Any

from functions.base.api_usage.handler import track_usage_middleware


logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn = boto3.client('stepfunctions')


def get_state_machine_arn(flow_name: str) -> str:
    """
    Constructs the State Machine ARN based on the flow name.
    All state machines are created by the serverless framework using the flow name.
    """
    account_id = boto3.client('sts').get_caller_identity()['Account']
    region = boto3.session.Session().region_name
    return f"arn:aws:states:{region}:{account_id}:stateMachine:{flow_name}"


@track_usage_middleware
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handles the API Gateway event to start a Step Function execution.
    """
    try:
        # Extract flow name from path parameters
        flow_name = event['pathParameters']['flow_name']

        logger.info(f"Getting userId")
        # Get user ID from JWT claims (HTTP API format)
        user_id = event['requestContext']['authorizer']['jwt']['claims']['sub']
        logger.info(f"userId: {user_id}")

        # Get the state machine ARN
        state_machine_arn = get_state_machine_arn(flow_name)

        # Parse request body if present, otherwise use empty dict
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])

        # Add user ID to input
        execution_input = {
            **body,
            '__user_id': user_id
        }

        # Start the state machine execution with user ID
        response = sfn.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps(execution_input)
        )

        logger.info(f"Started execution of flow {flow_name} with ARN {response['executionArn']}")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": f"Started {flow_name}",
                "executionArn": response['executionArn'],
                "status": "SUCCESS"
            })
        }

    except sfn.exceptions.StateMachineDoesNotExist:
        logger.error(f"Flow {flow_name} not found")
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": f"Flow '{flow_name}' not found",
                "status": "ERROR"
            })
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request body")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Invalid JSON in request body",
                "status": "ERROR"
            })
        }

    except Exception as e:
        logger.error(f"Error starting flow execution: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "status": "ERROR"
            })
        }
