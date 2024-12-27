# functions/lib/hello_world/handler.py

import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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