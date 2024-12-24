# functions/process_data/handler.py
import json
import random


def handler(event, context):
    """
    First step: Process incoming data
    Simulates data processing by adding random metrics
    """
    print(f"ProcessData received event: {event}")

    # Simulate some processing
    processed_data = {
        "input": event,
        "metrics": {
            "processing_score": random.uniform(0, 100),
            "quality_index": random.uniform(0, 1),
            "timestamp": "2024-01-01T00:00:00Z"
        }
    }

    print(f"ProcessData output: {processed_data}")
    return processed_data