# functions/lib/hello_world/handler.py
import logging
from functions.base.api_usage.handler import track_usage_middleware


# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


@track_usage_middleware
def handler(event, context):
    logger.info('Event received: %s', event)

    try:
        return {
            "message": "Hello World!",
            "input": event
        }
    except Exception as e:
        logger.error('Error: %s', str(e))
        raise