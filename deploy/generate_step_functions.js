// deploy/generate_step_functions.js
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

// Custom YAML types for CloudFormation intrinsic functions
const getAtt = new yaml.Type('!GetAtt', {
  kind: 'scalar',
  construct: function (data) {
    return { 'Fn::GetAtt': data.split('.') };
  }
});

const ref = new yaml.Type('!Ref', {
  kind: 'scalar',
  construct: function (data) {
    return { Ref: data };
  }
});

const cfSchema = yaml.DEFAULT_SCHEMA.extend([getAtt, ref]);

module.exports = () => {
  const resources = {};

  // Create Step Functions execution role first
  resources.StepFunctionsExecutionRole = {
    Type: 'AWS::IAM::Role',
    Properties: {
      AssumeRolePolicyDocument: {
        Version: '2012-10-17',
        Statement: [{
          Effect: 'Allow',
          Principal: {
            Service: 'states.amazonaws.com'
          },
          Action: 'sts:AssumeRole'
        }]
      },
      ManagedPolicyArns: [
        'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
      ],
      Policies: [{
        PolicyName: 'StepFunctionsExecutionPolicy',
        PolicyDocument: {
          Version: '2012-10-17',
          Statement: [{
            Effect: 'Allow',
            Action: [
              'lambda:InvokeFunction'
            ],
            Resource: '*'
          }]
        }
      }]
    }
  };

  // Read flow definitions
  const flowsDir = path.join(__dirname, '..', 'flows');
  const flowFiles = fs.readdirSync(flowsDir).filter(file =>
    file.endsWith('.yml') || file.endsWith('.yaml')
  );

  flowFiles.forEach(file => {
    const flowContent = yaml.load(
      fs.readFileSync(path.join(flowsDir, file), 'utf8'),
      { schema: cfSchema }
    );

    if (!flowContent || !flowContent.name || !flowContent.definition) {
      console.warn(`Skipping invalid flow file: ${file}`);
      return;
    }

    // Create Lambda functions defined in the flow
    if (flowContent.functions) {
      flowContent.functions.forEach(func => {
        const functionName = func.name;
        resources[functionName] = {
          Type: 'AWS::Lambda::Function',
          Properties: {
            FunctionName: functionName,
            Handler: func.handler,
            Runtime: func.runtime || 'python3.9',
            Code: {
              ZipFile: `
                def handler(event, context):
                    return {
                        'statusCode': 200,
                        'body': 'Hello from ' + context.function_name
                    }
              `
            },
            Role: { 'Fn::GetAtt': ['IamRoleLambdaExecution', 'Arn'] }
          }
        };
      });
    }

    // Prepare variables for Fn::Sub
    const variables = {};
    if (flowContent.functions) {
      flowContent.functions.forEach(func => {
        variables[`${func.name}Arn`] = { 'Fn::GetAtt': [func.name, 'Arn'] };
      });
    }

    // Create state machine
    resources[`${flowContent.name}StateMachine`] = {
      Type: 'AWS::StepFunctions::StateMachine',
      DependsOn: ['StepFunctionsExecutionRole'].concat(
        flowContent.functions?.map(f => f.name) || []
      ),
      Properties: {
        StateMachineName: flowContent.name,
        DefinitionString: {
          'Fn::Sub': [
            JSON.stringify(flowContent.definition),
            variables
          ]
        },
        RoleArn: { 'Fn::GetAtt': ['StepFunctionsExecutionRole', 'Arn'] }
      }
    };
  });

  return { Resources: resources };
};