# Serverless Dynamic Workflows

**Serverless Dynamic Workflows** is a framework that lets you create, deploy and call Python functions in two ways:
1. As standalone REST endpoints - automatically generated from Python scripts in `functions/lib/`
2. As part of workflows - combine multiple Python scripts into orchestrated flows

## Table of Contents
- [Features](#features)
  - [Function Management](#function-management)
  - [Workflow Capabilities](#workflow-capabilities)
  - [Security & Authentication](#security--authentication)
  - [Development Tools](#development-tools)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Adding Functions](#adding-functions)
- [Creating Workflows](#creating-workflows)
- [Using Private Plugins](#using-private-plugins)
  - [Create a Plugin](#create-a-plugin)
  - [Use a Plugin](#use-a-plugin)
- [Advanced Features](#advanced-features)
  - [Scheduled Workflows](#scheduled-workflows)
  - [Composite Workflows](#composite-workflows)
  - [Long-Running Tasks (Over 30 Seconds)](#long-running-tasks-over-30-seconds)
  - [Secrets Management](#secrets-management)
  - [API Usage Tracking](#api-usage-tracking)
    - [Data Structure](#data-structure)
    - [Adding Usage Tracking to Custom Functions](#adding-usage-tracking-to-custom-functions)
    - [Retrieving Usage Data](#retrieving-usage-data)
    - [Usage Data Retention](#usage-data-retention)
  - [Lambda Permissions Management](#lambda-permissions-management)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Cleanup](#cleanup)
- [Security](#security)
- [Contributing](#contributing)
- [License](#license)

## Features

### Function Management
- **Auto-generated REST Endpoints**: Python functions in `functions/lib/` automatically get secure REST endpoints
- **Plugin Support**: Extend functionality through private repositories
- **Single API Entry Point**: Execute any function through a unified REST API

### Workflow Capabilities
- **Beyond Timeout Endpoints**: Execute Python scripts exceeding 30s (http timeout) using flows and polling for the result
- **Dynamic Flow Discovery**: Flows defined in YAML files are automatically deployed as AWS Step Functions
- **Scheduled Executions**: Create flows that run on a schedule using CloudWatch Events
- **Composite Flows**: Orchestrate multiple flows to run in parallel or sequence
- **Simple Flow Definitions**: Define workflows in YAML with automatic Lambda creation

### Security & Authentication
- **Cognito Integration**: Secure API endpoints with JWT tokens
- **Usage Tracking**: Built-in API usage tracking per user
- **Secrets Management**: Secure handling of API keys and secrets via AWS Parameter Store

### Development Tools
- **Admin Tools**: Built-in user management and token generation
- **Testing Framework**: Comprehensive testing tools for flows and functions
- **Plugin System**: Extend functionality through private repositories

## Prerequisites

- Python 3.9+
- Node.js 14+
- AWS CLI configured
- Serverless Framework (`npm install -g serverless`)
- GitHub personal access token (if using private plugins)
- Required AWS IAM permissions (see below)

### Required IAM Permissions

The user deploying this framework needs specific AWS permissions. You can create the required IAM policy using the following steps:

1. Create a file named `policy.json` with the required permissions. You can find the complete policy [here](./policy.json).

2. Replace these placeholders in the policy file:
   - `${region}` with your AWS region (e.g., `us-east-1`)
   - `${account-id}` with your AWS account ID

3. Create the policy in AWS:
```bash
aws iam create-policy \
    --policy-name serverless-dynamic-workflows-policy \
    --policy-document file://policy.json
```

## Installation

1. Clone and setup:
```bash
git clone https://github.com/your-username/serverless-dynamic-workflows.git
cd serverless-dynamic-workflows

# Install Node.js dependencies
npm install

# Install Python dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r layer/requirements.txt

# Initialize plugins config
echo '{"plugins":[]}' > config.json
```

2. Deploy:
```bash
serverless deploy
```

3. Create a user and get a token:
```bash
./admin_tools/create_user.py --email your@email.com
./admin_tools/get_user_token.py --email your@email.com
```

## Adding Functions

1. Create a new function:
```bash
mkdir functions/lib/my-function
```

2. Add handler code:
```python
# functions/lib/my-function/handler.py
def handler(event, context):
    return {
        "statusCode": 200,
        "body": {"message": "Hello from my function"}
    }
```

The function is automatically available at `POST /lib/my-function`

## Creating Workflows

1. Create a flow definition:
```yaml
# flows/myflow.yml
name: myFlow
description: Example workflow
definition:
  StartAt: Step1
  States:
    Step1:
      Type: Task
      Resource: "${Step1FunctionArn}"
      End: true

functions:
  - name: Step1Function
    handler: functions/lib/my-function/handler.handler
```

2. Deploy to update:
```bash
serverless deploy
```

## Using Private Plugins

Extend functionality by creating private repositories with additional functions and flows.

### Create a Plugin

1. Generate plugin structure:
```bash
chmod +x scripts/create-private-plugin.py
./scripts/create-private-plugin.py my-private-plugin
```

2. Add functions and flows:
```
my-private-plugin/
├── flows/              # Private workflow definitions
├── functions/
│   └── lib/           # Private function implementations
├── tests/
│   └── functions-lib/ # Tests for private functions
├── index.js           # Plugin entry point
└── package.json
```

3. Push to private repository:
```bash
cd my-private-plugin
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-org/my-private-plugin.git
git push -u origin main
```

### Use a Plugin

1. Add to config.json:
```json
{
  "plugins": [
    "git+https://YOUR_TOKEN@github.com/your-org/my-private-plugin.git"
  ]
}
```

2. Deploy as usual:
```bash
serverless deploy
```

## Advanced Features

### Scheduled Workflows

Create flows that run on a schedule using CloudWatch Events:
```yaml
# flows/scheduledFlow.yml
name: scheduledFlow
schedule: cron(0 12 * * ? *)  # Runs daily at 12 PM UTC
input:  # Optional static input
  message: "Scheduled execution"
definition:
  StartAt: Step1
  States:
    Step1:
      Type: Task
      Resource: "${Step1FunctionArn}"
      End: true
```

Schedule expressions support:
- Cron: `cron(0 12 * * ? *)`  # Daily at noon UTC
- Rate: `rate(5 minutes)`      # Every 5 minutes

### Composite Workflows

Create flows that orchestrate other flows:
```yaml
name: compositeFlow
definition:
  StartAt: ParallelSteps
  States:
    ParallelSteps:
      Type: Parallel
      Branches:
      - StartAt: Flow1
        States:
          Flow1:
            Type: Task
            Resource: "arn:aws:states:::states:startExecution"
            Parameters:
              StateMachineArn: "${flow1StateMachine}"
              Input.$: "$"
            End: true
      End: true

stateMachineReferences:
  - flow1StateMachine
```

### Long-Running Tasks (Over 30 Seconds)

API Gateway enforces a 29-second timeout for synchronous calls. To handle tasks that run longer (up to 15 minutes):

1. **Start Flow (POST):** Immediately triggers a Step Functions execution and returns an `executionArn`.  
2. **Poll Status (GET):** The client uses the `executionArn` to poll for final status (`RUNNING`, `SUCCEEDED`, or `FAILED`).

### Secrets Management

Use AWS Systems Manager Parameter Store for secure secrets:

1. Store secrets:
```bash
aws ssm put-parameter \
    --name "/serverless-dynamic-workflows/${STAGE}/API_KEY" \
    --type SecureString \
    --value "your-api-key-here"
```

2. Access in functions:
```python
import os

def handler(event, context):
    api_key = os.environ.get('API_KEY')
    # Use API key securely
```

### API Usage Tracking

#### Data Structure
DynamoDB schema for usage tracking:
- `userId`: User's Cognito ID (Hash Key)
- `yearMonth`: YYYY-MM format (Range Key)
- `apiCalls`: Total API calls that month
- `ttl`: 90-day auto-cleanup

#### Adding Usage Tracking to Custom Functions
```python
from functions.base.api_usage.handler import track_usage_middleware

@track_usage_middleware
def handler(event, context):
    return {"status": "success"}
```

#### Retrieving Usage Data
```bash
# By email
./admin_tools/get_user_usage.py --email user@example.com

# By user ID
./admin_tools/get_user_usage.py --user-id abc123

# Last 3 months
./admin_tools/get_user_usage.py --email user@example.com --months 3
```

#### Usage Data Retention
- 90-day retention via DynamoDB TTL
- Monthly granularity for billing
- Fault-tolerant tracking

### Lambda Permissions Management

To grant your Python functions access to AWS services, add the required permissions to `lambda-permissions.yml`:

```yaml
# lambda-permissions.yml
iamRoleStatements:
  - Effect: Allow
    Action:
      - s3:PutObject
      - s3:GetObject
    Resource:
      - "arn:aws:s3:::events-*"
      - "arn:aws:s3:::events-*/*"
  # Add new permissions here
```

After adding new permissions, deploy your changes:
```bash
serverless deploy
```

Your functions will automatically have access to the specified AWS services after deployment.

## API Reference

Core Endpoints:
- `GET /flows` - List available flows
- `POST /run/{flow_name}` - Execute a flow
- `GET /run/{flow_name}/{execution_id}` - Get execution result
- `GET /auth/config` - Get Cognito configuration
- `GET /auth/verify` - Verify token

Function Endpoints:
- `POST /lib/{function-name}` - Execute a specific function

## Testing

Run tests:
```bash
# All tests
python -m pytest

# Specific test
python -m pytest test/flows/test_flow_dummy_2step.py
```

## Cleanup

Remove all deployed resources:
```bash
serverless remove
```

## Security

- Cognito authentication on all endpoints
- JWT token authorization
- Least-privilege IAM roles
- DynamoDB for state management
- Proper CORS configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Create a Pull Request

## License

MIT License - see [LICENSE.txt](LICENSE.txt)