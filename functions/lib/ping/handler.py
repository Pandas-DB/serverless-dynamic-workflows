from functions.base.api_usage.handler import track_usage_middleware

@track_usage_middleware
def handler(event, context):
    return {
        "statusCode": 200,
        "body": "I am alive"
    }
