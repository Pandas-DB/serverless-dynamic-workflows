import os
import json
import boto3

sfn = boto3.client('stepfunctions')

def handler(event, context):
    flow_name = event['pathParameters']['flow_name']
    
    # Map from flow_name to the actual ARN of the state machine
    # You can store these ARNs in environment variables or build them dynamically.
    flows = {
      'myFlow1': os.environ.get('MY_FLOW_1_ARN'),
      'myFlow2': os.environ.get('MY_FLOW_2_ARN'),
      'myFlow3': os.environ.get('MY_FLOW_3_ARN')
    }

    # Check if the requested flow exists
    if flow_name not in flows:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Flow not found"})
        }
    
    # Start the state machine execution
    response = sfn.start_execution(
        stateMachineArn=flows[flow_name],
        input=json.dumps(event.get('body', {}))
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Started {flow_name}",
            "executionArn": response['executionArn']
        })
    }

