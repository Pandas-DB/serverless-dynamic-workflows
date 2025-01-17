# admin_tools/get_user_token
import boto3
import json
import argparse
import os
import sys


def get_token(email, password, client_id, user_pool_id, duration_value=None, duration_unit=None):
    """Get authentication token for a Cognito user"""
    cognito = boto3.client('cognito-idp')

    auth_params = {
        'USERNAME': email,
        'PASSWORD': password
    }

    if duration_value and duration_unit:
        auth_params['TOKEN_VALIDITY'] = {
            'value': duration_value,
            'unit': duration_unit
        }

    try:
        response = cognito.initiate_auth(
            ClientId=client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters=auth_params
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
    parser.add_argument('--duration-value', type=int, help='Token duration value (optional)')
    parser.add_argument('--duration-unit', choices=['hours', 'days', 'months'], help='Token duration unit (optional)')
    args = parser.parse_args()

    password = os.getenv('PASSWORD') if not args.password else args.password
    client_id = os.getenv('CLIENT_ID') if not args.client_id else args.client_id
    user_pool_id = os.getenv('USER_POOL_ID') if not args.user_pool_id else args.user_pool_id

    token_info = get_token(args.email, password, client_id, user_pool_id,
                          args.duration_value, args.duration_unit)

    print("\nToken retrieved successfully!")
    print("---------------------------")
    print(f"ID Token: {token_info['id_token']}")
    print(f"\nAccess Token: {token_info['access_token']}")
    print(f"\nRefresh Token: {token_info['refresh_token']}")
    print(f"Expires in: {token_info['expires_in']} seconds")


if __name__ == '__main__':
    main()