# functions/base/list_runs/handler.py
import json
import boto3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from functions.base.api_usage.handler import track_usage_middleware

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn = boto3.client('stepfunctions')
MAX_RESULTS = 100  # Adjust based on your needs


def get_all_state_machines() -> List[str]:
    """Get all state machine ARNs in the account"""
    state_machines = []
    paginator = sfn.get_paginator('list_state_machines')

    for page in paginator.paginate():
        state_machines.extend([sm['stateMachineArn'] for sm in page['stateMachines']])

    return state_machines


def get_user_executions(state_machine_arn: str, user_id: str) -> List[Dict]:
    """Get executions for a specific state machine and filter by user_id"""
    user_executions = []
    ninety_days_ago = datetime.utcnow() - timedelta(days=90)

    paginator = sfn.get_paginator('list_executions')

    try:
        for page in paginator.paginate(
                stateMachineArn=state_machine_arn,
                maxResults=MAX_RESULTS
        ):
            for execution in page['executions']:
                try:
                    # Get execution details to check user_id
                    execution_details = sfn.describe_execution(
                        executionArn=execution['executionArn']
                    )
                    execution_input = json.loads(execution_details['input'])

                    # Only include if it belongs to the user
                    if execution_input.get('__user_id') == user_id:
                        user_executions.append({
                            'executionArn': execution['executionArn'],
                            'status': execution['status'],
                            'startDate': execution['startDate'].isoformat(),
                            'stopDate': execution.get('stopDate', '').isoformat() if 'stopDate' in execution else None,
                            'name': execution['name']
                        })
                except Exception as e:
                    logger.warning(f"Error processing execution {execution['executionArn']}: {str(e)}")
                    continue

    except Exception as e:
        logger.error(f"Error listing executions for state machine {state_machine_arn}: {str(e)}")

    return user_executions


@track_usage_middleware
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """List all executions for the authenticated user across all state machines"""
    try:
        # Get user ID from JWT claims
        user_id = event['requestContext']['authorizer']['jwt']['claims']['sub']

        # Get all state machines
        state_machines = get_all_state_machines()

        # Collect all executions for the user
        all_executions = []
        for sm_arn in state_machines:
            executions = get_user_executions(sm_arn, user_id)
            all_executions.extend(executions)

        # Sort by start date, most recent first
        all_executions.sort(key=lambda x: x['startDate'], reverse=True)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "executions": all_executions,
                "count": len(all_executions)
            })
        }

    except Exception as e:
        logger.error(f"Error listing executions: {str(e)}")
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