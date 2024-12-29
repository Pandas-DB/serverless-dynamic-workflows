# admin_tools/get_user_usage.py
import os
import boto3
import json
import argparse
import sys
from datetime import datetime, date
from dateutil.relativedelta import relativedelta


def get_table_name():
    """Get DynamoDB table name from CloudFormation outputs"""
    cf = boto3.client('cloudformation')

    try:
        stack_name = 'serverless-dynamic-workflows-dev'

        # The table name follows the pattern from serverless.yml: ${self:service}-api-usage-${self:provider.stage}
        # where service is 'serverless-dynamic-workflows' and stage is 'dev'
        service_name = 'serverless-dynamic-workflows'
        stage = 'dev'
        table_name = f"{service_name}-api-usage-{stage}"

        return table_name
    except Exception as e:
        print(f"Error getting table name: {str(e)}")
        sys.exit(1)


def get_usage_data(email=None, user_id=None, months=1):
    """Get API usage data for a user"""
    if not email and not user_id:
        print("Error: Either email or user_id must be provided")
        sys.exit(1)

    try:
        # If email is provided, get the user_id from Cognito
        if email and not user_id:
            cognito = boto3.client('cognito-idp')
            cf = boto3.client('cloudformation')

            # Get UserPoolId from CloudFormation outputs
            response = cf.describe_stacks(StackName='serverless-dynamic-workflows-dev')
            outputs = response['Stacks'][0]['Outputs']
            user_pool_id = next(o['OutputValue'] for o in outputs if o['OutputKey'] == 'UserPoolId')

            # Get user by email
            response = cognito.list_users(
                UserPoolId=user_pool_id,
                Filter=f'email = "{email}"'
            )

            if not response['Users']:
                print(f"No user found with email: {email}")
                sys.exit(1)

            user_id = response['Users'][0]['Username']

        # Get usage data from DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(get_table_name())

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - relativedelta(months=months - 1)

        # Format dates as YYYY-MM
        start_month = start_date.strftime('%Y-%m')
        end_month = end_date.strftime('%Y-%m')

        response = table.query(
            KeyConditionExpression='userId = :uid AND yearMonth BETWEEN :start AND :end',
            ExpressionAttributeValues={
                ':uid': user_id,
                ':start': start_month,
                ':end': end_month
            }
        )

        return {
            'userId': user_id,
            'email': email,
            'usage': response['Items']
        }

    except Exception as e:
        print(f"Error getting usage data: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Get API usage data for a user')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--email', help='Email address of the user')
    group.add_argument('--user-id', help='Cognito user ID')
    parser.add_argument('--months', type=int, default=1, help='Number of months to retrieve (default: 1)')
    args = parser.parse_args()

    email = os.getenv('EMAIL') if not args.email else args.email
    user_id = os.getenv('USER_ID') if not args.user_id else args.user_id

    usage_data = get_usage_data(email, user_id, args.months)

    print("\nAPI Usage Data")
    print("-------------")
    print(f"User ID: {usage_data['userId']}")
    if usage_data['email']:
        print(f"Email: {usage_data['email']}")

    if not usage_data['usage']:
        print("\nNo usage data found for the specified period.")
    else:
        print("\nMonthly Usage:")
        for item in usage_data['usage']:
            print(f"\nMonth: {item['yearMonth']}")
            print(f"Total API Calls: {item.get('apiCalls', 0)}")


if __name__ == '__main__':
    main()