import json
import boto3
from aws_lambda_powertools import Logger
from functions.base.api_usage.handler import track_usage_middleware

logger = Logger()
sfn = boto3.client('stepfunctions')


@track_usage_middleware
@logger.inject_lambda_context
def handler(event, context):
    execution_id = event['pathParameters']['execution_id']

    try:
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
