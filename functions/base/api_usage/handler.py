# functions/base/api_usage/handler.py
import os
import json
import boto3
import time
from datetime import datetime
from aws_lambda_powertools import Logger, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext
from boto3.dynamodb.conditions import Key

logger = Logger()
metrics = Metrics()
dynamodb = boto3.resource('dynamodb')


def get_table():
    """Lazy initialization of DynamoDB table connection"""
    if not hasattr(get_table, 'table'):
        table_name = os.environ.get('API_USAGE_TABLE')
        if table_name:
            get_table.table = dynamodb.Table(table_name)
        else:
            logger.warning("API_USAGE_TABLE environment variable not set - usage tracking disabled")
            get_table.table = None
    return get_table.table


def track_api_call(user_id: str, api_path: str, method: str) -> None:
    """Track a single API call for a user"""
    table = get_table()
    if not table:
        logger.warning("Usage tracking disabled - skipping API call tracking")
        return

    current_date = datetime.utcnow()
    year_month = current_date.strftime('%Y-%m')

    try:
        # First, initialize the item if it doesn't exist
        table.update_item(
            Key={
                'userId': user_id,
                'yearMonth': year_month
            },
            UpdateExpression='SET apiCalls = if_not_exists(apiCalls, :zero), #ttl = :ttl',
            ExpressionAttributeNames={
                '#ttl': 'ttl'
            },
            ExpressionAttributeValues={
                ':zero': 0,
                ':ttl': int(time.time()) + (90 * 24 * 60 * 60)
            }
        )

        # Then increment the counter
        table.update_item(
            Key={
                'userId': user_id,
                'yearMonth': year_month
            },
            UpdateExpression='ADD apiCalls :inc',
            ExpressionAttributeValues={
                ':inc': 1
            }
        )
    except Exception as e:
        logger.error(f"Error tracking API call: {str(e)}")
        # Don't raise the exception - we don't want to break the main functionality
        # if usage tracking fails


# Middleware for tracking API calls
def track_usage_middleware(handler):
    def wrapper(event, context):
        try:
            # Extract user ID from Cognito authorizer context
            auth_context = event.get('requestContext', {}).get('authorizer', {})
            claims = auth_context.get('jwt', {}).get('claims', {})
            user_id = claims.get('sub')

            if user_id:
                # Track the API call
                api_path = event.get('requestContext', {}).get('http', {}).get('path')
                http_method = event.get('requestContext', {}).get('http', {}).get('method')
                track_api_call(user_id, api_path, http_method)

        except Exception as e:
            # Log the error but don't prevent the handler from executing
            logger.error(f"Error in usage tracking middleware: {str(e)}")

        # Call the original handler
        return handler(event, context)

    return wrapper


@logger.inject_lambda_context
def get_usage(event: dict, context: LambdaContext) -> dict:
    """Get API usage for a user"""
    table = get_table()
    if not table:
        return {
            'statusCode': 503,
            'body': json.dumps({'error': 'Usage tracking is not configured'})
        }

    user_id = event['pathParameters']['userId']

    # Optional date filtering
    start_date = event.get('queryStringParameters', {}).get('startDate')
    end_date = event.get('queryStringParameters', {}).get('endDate')

    try:
        # Query usage records for the user
        query_params = {
            'KeyConditionExpression': Key('userId').eq(user_id)
        }

        if start_date and end_date:
            query_params['KeyConditionExpression'] &= Key('yearMonth').between(start_date, end_date)

        response = table.query(**query_params)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'userId': user_id,
                'usage': response['Items']
            })
        }
    except Exception as e:
        logger.error(f"Error getting usage data: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }