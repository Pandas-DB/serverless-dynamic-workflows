# Serverless Dynamic Workflows

**Serverless Dynamic Workflows** allows you to create and deploy Python script workflows triggered by an API REST so that you do not need to think of infrastructure

### Back-End Definition

**Serverless Dynamic Workflows** is a serverless application that enables dynamic creation and execution of AWS Step Functions workflows through YAML definitions. Each workflow is defined in a separate file in the `flows/` directory and is automatically deployed as a state machine. The application provides authenticated API endpoints to execute and manage these workflows.

## Key Features

- **Dynamic Flow Discovery**: Flows are defined in YAML files and automatically deployed as Step Functions
- **Single API Entry Point**: Execute any flow through a unified REST API
- **Cognito Authentication**: Secure API endpoints with JWT tokens
- **Simple Flow Definitions**: Define workflows in YAML with automatic Lambda creation
- **Admin Tools**: Easy user management and token generation
- **Testing Tools**: Built-in flow testing capabilities

## Repository Structure

```
serverless-dynamic-workflows/
├── admin_tools/                # Admin utilities
│   ├── create_user.py         # Create Cognito users
│   └── get_user_token.py      # Generate authentication tokens
├── deploy/                    # Deployment scripts
│   ├── generate_step_functions.js
│   └── load_flows.js
├── flows/                     # Flow definitions, where you specify your scripts workflow
│   ├── dummy2StepFlow.yml
│   └── helloWorldFlow.yml
├── functions/                 # API Lambda handlers
│   ├── auth/                 # Authentication endpoints
│   ├── list_flows/          # List available flows
│   └── run_flow/            # Execute flows
├── scripts/                  # Flow Lambda functions. Where you put your Python scripts
│   ├── hello_world.py
│   ├── random_generator.py
│   └── transform_random_generator.py
├── test/                     # Test utilities
│   ├── api/                 # API tests
│   │   └── test_list_flows.py
│   └── flows/              # Flow tests
│       ├── test_flow_dummy_2step.py
│       └── test_flow_hello_world.py
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

### Listing Available Flows

```bash
./test/api/test_list_flows.py
```

Example output:
```
+------------------+---------------------------------+--------+---------------------+
| Name             | Description                     | States | Created            |
+==================+=================================+========+=====================+
| dummy2StepFlow   | A dummy two-step data pipeline | 2      | 2024-12-24T10:00Z  |
| helloWorldFlow   | A simple hello world workflow   | 1      | 2024-12-24T09:30Z  |
+------------------+---------------------------------+--------+---------------------+
```

### Running a Flow

```bash
./test/flows/test_flow_dummy_2step.py --input '{"test": true}'
```

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
    handler: scripts/my_script.handler
    runtime: python3.9
```

2. Add your Lambda function in `scripts/`:
```python
# scripts/my_script.py
def handler(event, context):
    return {"status": "success", "data": event}
```

3. Deploy the changes:
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