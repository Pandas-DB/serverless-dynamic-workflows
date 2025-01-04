# functions/base/get_flow_results/handler.py
import json
import boto3
from aws_lambda_powertools import Logger
from functions.base.api_usage.handler import track_usage_middleware

logger = Logger()
sfn = boto3.client('stepfunctions')


def verify_execution_owner(execution_arn: str, user_id: str) -> bool:
    try:
        execution = sfn.describe_execution(executionArn=execution_arn)
        execution_input = json.loads(execution['input'])
        return execution_input.get('__user_id') == user_id
    except:
        return False


@track_usage_middleware
@logger.inject_lambda_context
def handler(event, context):
    execution_id = event['pathParameters']['execution_id']
    logger.info(f"Getting userId")
    user_id = event['requestContext']['authorizer']['jwt']['claims']['sub']
    logger.info(f"userId: {user_id}")

    try:
        # Verify ownership (the user that makes the GET request is the same that triggered this flow)
        if not verify_execution_owner(execution_id, user_id):
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Not authorized to access this execution'})
            }

        execution = sfn.describe_execution(
            executionArn=execution_id
        )
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': execution['status'],
                'output': json.loads(execution.get('output', '{}')),
                'startDate': execution['startDate'].isoformat(),
                'stopDate': execution.get('stopDate', '').isoformat() if 'stopDate' in execution else None
            })
        }
    except Exception as e:
        logger.exception('Failed to get execution result')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
