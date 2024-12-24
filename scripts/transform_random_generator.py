# functions/transform_data/handler.py
import json


def handler(event, context):
    """
    Second step: Transform the processed data
    Takes the output from ProcessData and adds some transformations
    """
    print(f"TransformData received event: {event}")

    # Get the metrics from previous step
    input_metrics = event.get('metrics', {})

    # Simulate some transformations
    transformed_data = {
        "original_data": event,
        "transformations": {
            "normalized_score": input_metrics.get('processing_score', 0) / 100,
            "quality_category": "HIGH" if input_metrics.get('quality_index', 0) > 0.5 else "LOW",
            "status": "COMPLETED"
        }
    }

    print(f"TransformData output: {transformed_data}")
    return transformed_data