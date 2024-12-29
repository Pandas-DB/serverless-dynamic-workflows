# Serverless Dynamic Workflows

**Serverless Dynamic Workflows** allows you to create, deploy and call Python scripts in two ways:
1. As standalone REST endpoints - simply add your Python scripts to `functions/lib/` and it automatically gets its own authenticated endpoint
2. As part of workflows - combine multiple Python scripts into workflows

### Back-End Definition

**Serverless Dynamic Workflows** is a serverless application that:
- Auto-generates REST endpoints from Python functions in `functions/lib/`
- Enables creation of multi-step workflows through YAML definitions in `flows/`
- Deploys workflows as AWS Step Functions state machines
- Provides authenticated API endpoints to execute and manage both standalone functions and workflows

## Key Features

- **Dynamic Flow Discovery**: Flows are defined in YAML files and automatically deployed as Step Functions
- **Single API Entry Point**: Execute any flow through a unified REST API
- **Cognito Authentication**: Secure API endpoints with JWT tokens
- **Simple Flow Definitions**: Define workflows in YAML with automatic Lambda creation
- **Scheduled Flows**: Create flows that run on a schedule using CloudWatch Events
- **Composite Flows**: Orchestrate multiple flows to run in parallel or sequence
- **Admin Tools**: Easy user management and token generation
- **Testing Tools**: Built-in flow testing capabilities
- **Auto-generated Endpoints**: Each function in lib/ automatically gets its own REST endpoint under the `/lib` prefix
- **Plugin-based Function Loading**: Uses a custom Serverless plugin to dynamically load and configure library functions

## Repository Structure

```
serverless-dynamic-workflows/
├── admin_tools
│   ├── create_user.py
│   ├── get_user_token.py
│   └── get_user_usage.py
├── AUTHORS.rst
├── deploy
│   ├── generate-step-functions.js
│   ├── load_flows.js
│   └── serverless-dynamic-functions.js
├── flows
│   ├── compositeFlow.yml
│   ├── dummy2StepFlow.yml
│   ├── helloWorldFlow.yml
│   ├── scheduleFlow.yml
│   └── scheduleMapFlow.yml
├── functions
│   ├── base
│   │   ├── api_usage
│   │   │   ├── handler.py
│   │   │   └── __init__.py
│   │   ├── auth
│   │   │   └── __init__.py
│   │   ├── get_flow_result
│   │   │   ├── handler.py
│   │   │   └── __init__.py
│   │   ├── list_flows
│   │   │   ├── handler.py
│   │   │   └── __init__.py
│   │   └── run_flow
│   │       ├── handler.py
│   │       └── __init__.py
│   └── lib
│       ├── dummy_check
│       │   ├── handler.py
│       │   └── __init__.py
│       ├── hello_world
│       │   ├── handler.py
│       │   └── __init__.py
│       └── ping
│           ├── handler.py
│           └── __init__.py
├── LICENSE.txt
├── package.json
├── package-lock.json
├── README.md
├── serverless.yml
└── test
    ├── api
    │   ├── test_api_usage.py
    │   └── test_list_flows.py
    ├── flows
    │   ├── test_flow_composite.py
    │   ├── test_flow_dummy_2step.py
    │   └── test_flow_hello_world.py
    └── functions-lib
        └── test_ping.py
```

## Prerequisites

- Python 3.9+
- Node.js 14+
- AWS CLI configured
- Serverless Framework (`npm install -g serverless`)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/serverless-dynamic-workflows.git
cd serverless-dynamic-workflows
```

2. Install dependencies:
```bash
# Install Node.js dependencies
npm install

# Install Python dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r layer/requirements.txt
```

## Deployment

Deploy the application:
```bash
serverless deploy
```

## Authentication Setup

1. Create a new user:
```bash
./admin_tools/create_user.py --email your@email.com
```

2. Get an authentication token:
```bash
./admin_tools/get_user_token.py --email your@email.com
```

## Secrets Management

The application uses AWS Systems Manager Parameter Store for managing secrets securely. To add secrets for third-party API integrations:

1. Store secrets using AWS CLI:

```bash
# Store an API key
aws ssm put-parameter \
    --name "/serverless-dynamic-workflows/${STAGE}/API_KEY" \
    --type SecureString \
    --value "your-api-key-here"

# Store an API secret
aws ssm put-parameter \
    --name "/serverless-dynamic-workflows/${STAGE}/API_SECRET" \
    --type SecureString \
    --value "your-secret-here"

# Replace ${STAGE} with 'dev', 'prod', etc.
```

2. Or using AWS Console:

- Navigate to AWS Systems Manager > Parameter Store
- Click "Create parameter"
- Name: /serverless-dynamic-workflows/${STAGE}/PARAMETER_NAME
- Type: SecureString
- Value: Your secret value

3. Access in your functions:

```python
# functions/lib/my-function/handler.py
import os

def handler(event, context):
    api_key = os.environ.get('API_KEY')
    api_secret = os.environ.get('API_SECRET')
    # Use these values for your API calls
```

## Usage

### Available Endpoints

The application provides two types of endpoints:

1. Core System Endpoints:
- `GET /flows` - List available flows
- `POST /run/{flow_name}` - Execute a flow
- `GET /run/{flow_name}/{execution_id}` - Get flow execution result
- `GET /auth/config` - Get Cognito configuration
- `GET /auth/verify` - Verify authentication token

2. Auto-generated Function Endpoints:
Each function in `functions/lib/` automatically gets its own endpoint:
- `POST /lib/hello-world` - Execute hello world function
- `POST /lib/ping` - Execute ping function
- `POST /lib/dummy-check` - Execute dummy check function

### Creating a New Function

1. Add a new directory in `functions/lib/`:
```bash
mkdir functions/lib/my-function
```

2. Create a handler file:
```python
# functions/lib/my-function/handler.py
def handler(event, context):
    return {"status": "success", "data": event}
```

The function will be automatically available at `POST /lib/my-function`

### Creating a New Flow

1. Create a flow definition in `flows/`:
```yaml
# flows/myNewFlow.yml
name: myNewFlow
description: My new workflow
definition:
  StartAt: FirstStep
  States:
    FirstStep:
      Type: Task
      Resource: "${FirstStepFunctionArn}"
      End: true

functions:
  - name: FirstStepFunction
    handler: functions/lib/my-function/handler.handler
    runtime: python3.9
```

2. Deploy the changes:
```bash
serverless deploy
```

### Creating a Scheduled Flow

You can create flows that run on a schedule using CloudWatch Events (EventBridge). Add a `schedule` property to your flow definition:

```yaml
# flows/scheduledFlow.yml
name: scheduledFlow
description: A workflow that runs on a schedule
schedule: cron(0 12 * * ? *)  # Runs daily at 12 PM UTC
input:  # Optional static input that will be passed to the flow
  message: "Scheduled execution"
definition:
  StartAt: FirstStep
  States:
    FirstStep:
      Type: Task
      Resource: "${FirstStepFunctionArn}"
      End: true

functions:
  - name: FirstStepFunction
    handler: functions/lib/my-function/handler.handler
    runtime: python3.9
```

Schedule expressions can use either:
- Cron expressions: `cron(0 12 * * ? *)`  # Runs daily at noon UTC
- Rate expressions: `rate(5 minutes)`      # Runs every 5 minutes

### Creating a Composite Flow

You can create flows that orchestrate other flows, running them in parallel or sequence. Use the special `arn:aws:states:::states:startExecution` resource to invoke other state machines:

```yaml
# flows/compositeFlow.yml
name: compositeFlow
description: A workflow that combines multiple flows
definition:
  StartAt: ParallelFlows
  States:
    ParallelFlows:
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
      - StartAt: Flow2
        States:
          Flow2:
            Type: Task
            Resource: "arn:aws:states:::states:startExecution"
            Parameters:
              StateMachineArn: "${flow2StateMachine}"
              Input.$: "$"
            End: true
      Next: Flow3
    Flow3:
      Type: Task
      Resource: "arn:aws:states:::states:startExecution"
      Parameters:
        StateMachineArn: "${flow3StateMachine}"
        Input.$: "$"
      End: true

# Reference the state machines that will be called
stateMachineReferences:
  - flow1StateMachine
  - flow2StateMachine
  - flow3StateMachine
```

This example:
1. Runs flow1 and flow2 in parallel
2. Waits for both to complete
3. Then runs flow3 sequentially

The `stateMachineReferences` section is required to properly link to other state machines. Use the exact name of the flow plus "StateMachine" suffix (e.g., "helloWorldFlowStateMachine" for a flow named "helloWorldFlow").

## API Usage Tracking

The application includes built-in API usage tracking per user and month. This is automatically enabled for core system endpoints and can be added to your custom functions.

### Data Structure

Usage data is stored in DynamoDB with the following structure:
- `userId`: User's Cognito ID (Hash Key)
- `yearMonth`: Month of usage in YYYY-MM format (Range Key)
- `apiCalls`: Total number of API calls for that month
- `ttl`: Automatic cleanup after 90 days

### Adding Usage Tracking to Custom Functions

1. Import the middleware in your function:
```python
# functions/lib/my-function/handler.py
from functions.base.api_usage.handler import track_usage_middleware

@track_usage_middleware
def handler(event, context):
    return {"status": "success", "data": event}
```

The middleware will automatically:
- Track API calls per authenticated user
- Store monthly usage statistics
- Handle error cases gracefully (won't affect your function if tracking fails)

### Retrieving Usage Data

Usage data can be retrieved using the admin tool:

```bash
# Get usage by email
./admin_tools/get_user_usage.py --email user@example.com

# Get usage by user ID
./admin_tools/get_user_usage.py --user-id abc123

# Get last 3 months of usage
./admin_tools/get_user_usage.py --email user@example.com --months 3
```

### Usage Data Retention

- Usage data is automatically cleaned up after 90 days using DynamoDB TTL
- Data is stored at month granularity for easier billing integration
- Failed tracking attempts won't affect your function execution


## API Endpoints

- `GET /flows` - List available flows
- `POST /run/{flow_name}` - Execute a flow
- `GET /auth/config` - Get Cognito configuration
- `GET /auth/verify` - Verify authentication token

## Testing

Run API tests:
```bash
python -m pytest test/api/

# Test specific flow
python test/flows/test_flow_dummy_2step.py
```

## Security

The application uses:
- Cognito User Pools for authentication
- JWT tokens for API authorization
- IAM roles with least privilege
- DynamoDB for state management
- Proper CORS configuration

## Cleanup

Remove all deployed resources:
```bash
serverless remove
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE.txt) file for details.