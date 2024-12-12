# Serverless Dynamic Flows

**Serverless Dynamic Flows** is a template repository that demonstrates how to dynamically generate, deploy, and run AWS Step Functions state machines based on separate flow definition files. Each flow definition is an isolated YAML file in the `flows/` directory. During the build process, the repository automatically discovers these flow files, creates a combined index, and deploys them as state machines. A single API endpoint (via API Gateway and Lambda) then provides a way to trigger any available flow by name.

## Key Features

- **Dynamic Flow Discovery:**  
  Flow definitions are kept in the `flows/` directory. No manual editing of `serverless.yml` is required when a new flow is added.
  
- **Automatic Step Function Creation:**  
  A pre-deployment script scans the `flows/` directory, generates an index file, and references them in `serverless.yml` via the Serverless Step Functions plugin.
  
- **Single Entry Point API:**  
  The `run_flow` Lambda function exposes a single API endpoint. By passing a `flow_name` path parameter, you can start the corresponding state machine execution.
  
- **Flexible and Scalable:**  
  Add new flows by simply adding a new `.yml` file into the `flows/` directory. The next deployment automatically includes it as a new state machine.

## Architecture Overview

1. **Flows Directory:**  
   Each file in `flows/` defines a Step Functions state machine in YAML or JSON format. For example:
   ```yaml
   Comment: "A simple flow"
   StartAt: InitialState
   States:
     InitialState:
       Type: Task
       Resource: arn:aws:lambda:eu-west-1:123456789012:function:my-initial-lambda
       Next: NextState
     NextState:
       Type: Pass
       End: true

2. **Pre-deployment Script:**  
   Before deployment, `scripts/build_flows_map.js` runs. It:
   - Lists all `.yml` files in `flows/`.
   - Generates `flows/index.yml`, containing references to all discovered flows.
   - Creates a `flows_map.json` file mapping flow names to their state machine logical IDs.

3. **Serverless Framework Deployment:**  
   `serverless.yml` is configured to:
   - Use the `index.yml` file to define Step Functions state machines.
   - Deploy the `run_flow` Lambda and other functions.
   - Set up an API Gateway endpoint that forwards requests to `run_flow`.

4. **Run Flow Endpoint:**  
   The `run_flow` Lambda handler reads the `flow_name` from the request path and uses it to look up the corresponding state machine ARN. It then calls `StartExecution` on that state machine.

## Getting Started

### Prerequisites

- **Node.js and NPM:**  
  Needed to run scripts and install the Serverless Framework.
  
- **Serverless Framework:**  
  Install globally or locally:
  ```bash
  npm install -g serverless

- **AWS Credentials:**  
  Configure your environment:
  ```bash
  aws configure

### Installation

1. **Clone the Repo:**
   ```bash
   git clone https://github.com/your-username/serverless-dynamic-flows.git
   cd serverless-dynamic-flows

2. **Install Dependencies:**
   ```bash
   npm install

3. **Add or Modify Flow Files (Optional):** Add your flow definitions in flows/. For example:

cp examples/myFlow1.yml flows/

You can have multiple files like myFlow2.yml, myFlow3.yml, etc


### Deployment

Run the pre-deployment script and then deploy:

```bash
npm run predeploy
serverless deploy

**What happens during deployment?**

- The `predeploy` script (`scripts/build_flows_map.js`) runs and generates `flows/index.yml` and `flows/flows_map.json`.
- The `serverless deploy` command:
  - Deploys all state machines defined in `index.yml`.
  - Deploys the `run_flow` function and others defined in `serverless.yml`.
  - Sets up an API Gateway endpoint at:  
    `https://<api-id>.execute-api.<region>.amazonaws.com/<stage>/flows/{flow_name}`
    
    
### Usage

**Starting a Flow Execution:**

Once deployed, trigger a flow by its name:

```bash
curl -X POST \
  https://<api-id>.execute-api.<region>.amazonaws.com/<stage>/flows/myFlow1 \
  -H "Content-Type: application/json" \
  -d '{"key":"value"}'

A successful response returns the `executionArn` of the started execution.

### Adding New Flows

To add a new flow:

1. Create a new file in `flows/`, e.g. `myFlowNew.yml`.
2. Re-run the pre-deployment and deploy:
   ```bash
   npm run predeploy
   serverless deploy

3. Invoke the new flow:
   ```bash
   curl -X POST https://<api-id>.execute-api.<region>.amazonaws.com/<stage>/flows/myFlowNew

### Cleaning Up

To remove all resources:
```bash
serverless remove

This removes deployed functions, state machines, and other AWS resources created by the stack.

## Contributing

Contributions are welcome! If you have ideas or issues:

1. Open an issue describing the problem or suggestion.
2. Submit a pull request with proposed changes.

## License

This project is licensed under the [MIT License](LICENSE).
