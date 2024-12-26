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
- **Admin Tools**: Easy user management and token generation
- **Testing Tools**: Built-in flow testing capabilities
- **Auto-generated Endpoints**: Each function in lib/ automatically gets its own REST endpoint under the `/lib` prefix
- **Plugin-based Function Loading**: Uses a custom Serverless plugin to dynamically load and configure library functions

## Repository Structure

```
serverless-dynamic-workflows/
├── admin_tools/                # Admin utilities
│   ├── create_user.py         # Create Cognito users
│   └── get_user_token.py      # Generate authentication tokens
├── deploy/                    # Deployment scripts
│   ├── generate_step_functions.js
│   ├── generate_lib_functions.js
│   └── load_flows.js
├── flows/                     # Flow definitions
│   ├── dummy2StepFlow.yml
│   └── helloWorldFlow.yml
├── functions/                 # Lambda functions
│   ├── base/                 # Core functionality
│   │   ├── auth/            # Authentication endpoints
│   │   ├── list_flows/      # List available flows
│   │   └── run_flow/        # Execute flows
│   └── lib/                  # Reusable functions
│       ├── hello_world/     # Each folder becomes an endpoint
│       ├── ping/
│       └── dummy_check/
├── test/                     # Test utilities
│   ├── api/                 # API tests
│   └── flows/              # Flow tests
├── layer/                   # Lambda layers
│   └── requirements.txt
└── serverless.yml          # Infrastructure definition
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