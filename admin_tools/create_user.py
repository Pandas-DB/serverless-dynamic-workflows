#!/usr/bin/env python3
import boto3
import json
import argparse
import os
import string
import random
import sys

def generate_password():
    """Generate a strong random password"""
    length = 12
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(random.choice(chars) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password

def get_cognito_ids():
    """Get Cognito Pool ID and Client ID from CloudFormation outputs"""
    cf = boto3.client('cloudformation')
    
    try:
        response = cf.describe_stacks(StackName='serverless-dynamic-workflows-dev')
        outputs = response['Stacks'][0]['Outputs']
        
        user_pool_id = next(o['OutputValue'] for o in outputs if o['OutputKey'] == 'UserPoolId')
        client_id = next(o['OutputValue'] for o in outputs if o['OutputKey'] == 'UserPoolClientId')
        
        return user_pool_id, client_id
    except Exception as e:
        print(f"Error getting Cognito IDs: {str(e)}")
        sys.exit(1)

def create_user(email):
    """Create a new Cognito user"""
    user_pool_id, client_id = get_cognito_ids()
    password = generate_password()
    
    cognito = boto3.client('cognito-idp')
    
    try:
        # Create user
        cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            TemporaryPassword=password,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            MessageAction='SUPPRESS'  # Don't send email
        )
        
        # Set permanent password
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=email,
            Password=password,
            Permanent=True
        )
        
        return {
            'email': email,
            'password': password,
            'user_pool_id': user_pool_id,
            'client_id': client_id
        }
        
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Create a Cognito user')
    parser.add_argument('--email', required=True, help='Email address for the new user')
    args = parser.parse_args()
    
    user_info = create_user(args.email)
    
    print("\nUser created successfully!")
    print("------------------------")
    print(f"Email: {user_info['email']}")
    print(f"Password: {user_info['password']}")
    print(f"User Pool ID: {user_info['user_pool_id']}")
    print(f"Client ID: {user_info['client_id']}")


if __name__ == '__main__':
    main()
