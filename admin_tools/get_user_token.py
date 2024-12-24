#!/usr/bin/env python3
import boto3
import json
import argparse
import os
import sys

def get_token(email, password, client_id=None, user_pool_id=None):
    """Get authentication token for a Cognito user"""
    # If no client_id provided, try to load from credentials file
    if not client_id or not user_pool_id:
        try:
            with open('user_credentials.json', 'r') as f:
                creds = json.load(f)
                client_id = client_id or creds['client_id']
                user_pool_id = user_pool_id or creds['user_pool_id']
                # If no password provided, use from file
                if not password and email == creds['email']:
                    password = creds['password']
        except FileNotFoundError:
            cf = boto3.client('cloudformation')
            try:
                response = cf.describe_stacks(StackName='serverless-dynamic-workflows-dev')
                outputs = response['Stacks'][0]['Outputs']
                client_id = next(o['OutputValue'] for o in outputs if o['OutputKey'] == 'UserPoolClientId')
                user_pool_id = next(o['OutputValue'] for o in outputs if o['OutputKey'] == 'UserPoolId')
            except Exception as e:
                print(f"Error getting Cognito IDs: {str(e)}")
                sys.exit(1)
    
    cognito = boto3.client('cognito-idp')
    
    try:
        response = cognito.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        return {
            'id_token': response['AuthenticationResult']['IdToken'],
            'access_token': response['AuthenticationResult']['AccessToken'],
            'refresh_token': response['AuthenticationResult']['RefreshToken'],
            'expires_in': response['AuthenticationResult']['ExpiresIn']
        }
        
    except Exception as e:
        print(f"Error getting token: {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Get Cognito authentication token')
    parser.add_argument('--email', required=True, help='User email address')
    parser.add_argument('--password', help='User password (will try to load from credentials file if not provided)')
    parser.add_argument('--client-id', help='Cognito Client ID (optional)')
    parser.add_argument('--user-pool-id', help='Cognito User Pool ID (optional)')
    args = parser.parse_args()
    
    token_info = get_token(args.email, args.password, args.client_id, args.user_pool_id)
    
    print("\nToken retrieved successfully!")
    print("---------------------------")
    print(f"ID Token: {token_info['id_token']}")
    print(f"\nAccess Token: {token_info['access_token']}")
    print(f"\nRefresh Token: {token_info['refresh_token']}")
    print(f"Expires in: {token_info['expires_in']} seconds")

if __name__ == '__main__':
    main()
