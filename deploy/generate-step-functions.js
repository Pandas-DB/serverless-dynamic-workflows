// deploy/generate-step-functions.js
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const cfSchema = yaml.DEFAULT_SCHEMA.extend([
  new yaml.Type('!GetAtt', {
    kind: 'scalar',
    construct: data => ({ 'Fn::GetAtt': data.split('.') })
  }),
  new yaml.Type('!Ref', {
    kind: 'scalar',
    construct: data => ({ Ref: data })
  })
]);

module.exports = async () => {
  const resources = {};

  resources.StepFunctionsExecutionRole = {
    Type: 'AWS::IAM::Role',
    Properties: {
      AssumeRolePolicyDocument: {
        Version: '2012-10-17',
        Statement: [{
          Effect: 'Allow',
          Principal: { Service: 'states.amazonaws.com' },
          Action: 'sts:AssumeRole'
        }]
      },
      ManagedPolicyArns: [
        'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
        'arn:aws:iam::aws:policy/CloudWatchLogsFullAccess'
      ],
      Policies: [{
        PolicyName: 'StepFunctionsExecutionPolicy',
        PolicyDocument: {
          Version: '2012-10-17',
          Statement: [{
            Effect: 'Allow',
            Action: [
              'lambda:InvokeFunction',
              'states:StartExecution'
            ],
            Resource: '*'
          }]
        }
      }]
    }
  };

  resources.EventBridgeExecutionRole = {
    Type: 'AWS::IAM::Role',
    Properties: {
      AssumeRolePolicyDocument: {
        Version: '2012-10-17',
        Statement: [{
          Effect: 'Allow',
          Principal: { Service: 'events.amazonaws.com' },
          Action: 'sts:AssumeRole'
        }]
      },
      Policies: [{
        PolicyName: 'EventBridgeStepFunctionsPolicy',
        PolicyDocument: {
          Version: '2012-10-17',
          Statement: [{
            Effect: 'Allow',
            Action: ['states:StartExecution'],
            Resource: '*'
          }]
        }
      }]
    }
  };

  resources.StateMachineLogGroup = {
    Type: 'AWS::Logs::LogGroup',
    Properties: {
      LogGroupName: {
        'Fn::Sub': '/aws/vendedlogs/states/${self:service}-${self:provider.stage}'
      },
      RetentionInDays: 14
    }
  };

  const flowsDir = path.join(__dirname, '..', 'flows');
  const flowFiles = fs.readdirSync(flowsDir).filter(f => f.endsWith('.yml') || f.endsWith('.yaml'));

  for (const file of flowFiles) {
    const flowContent = yaml.load(fs.readFileSync(path.join(flowsDir, file), 'utf8'), { schema: cfSchema });
    if (!flowContent?.name || !flowContent?.definition) continue;

    const variables = {};

    // Handle function ARNs
    if (flowContent.functions) {
      flowContent.functions.forEach(func => {
        const handlerParts = func.handler.split('/');
        const functionDir = handlerParts[handlerParts.length - 2];

        const normalizedName = functionDir
          .replace(/-/g, '_')
          .replace(/[^a-zA-Z0-9_]/g, '')
          .replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
        const functionName = `lib${normalizedName.charAt(0).toUpperCase()}${normalizedName.slice(1)}`;

        variables[`${func.name}Arn`] = {
          'Fn::GetAtt': [`${functionName}`, 'Arn']
        };
      });
    }

    // Handle state machine references
    if (flowContent.stateMachineReferences) {
      flowContent.stateMachineReferences.forEach(stateMachineName => {
        variables[stateMachineName] = {
          'Fn::GetAtt': [`${stateMachineName}`, 'Arn']
        };
      });
    }

    // Get function dependencies
    const functionDependencies = flowContent.functions
      ? flowContent.functions.map(func => {
          const handlerParts = func.handler.split('/');
          const functionDir = handlerParts[handlerParts.length - 2];
          const normalizedName = functionDir
            .replace(/-/g, '_')
            .replace(/[^a-zA-Z0-9_]/g, '')
            .replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
          return `lib${normalizedName.charAt(0).toUpperCase()}${normalizedName.slice(1)}`;
        })
      : [];

    resources[`${flowContent.name}StateMachine`] = {
      Type: 'AWS::StepFunctions::StateMachine',
      DependsOn: ['StepFunctionsExecutionRole', 'StateMachineLogGroup', ...functionDependencies],
      Properties: {
        StateMachineName: flowContent.name,
        DefinitionString: {
          'Fn::Sub': [
            JSON.stringify(flowContent.definition),
            variables
          ]
        },
        RoleArn: { 'Fn::GetAtt': ['StepFunctionsExecutionRole', 'Arn'] },
        LoggingConfiguration: {
          Level: 'ALL',
          IncludeExecutionData: true,
          Destinations: [{
            CloudWatchLogsLogGroup: {
              LogGroupArn: {
                'Fn::Sub': 'arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/vendedlogs/states/${self:service}-${self:provider.stage}:*'
              }
            }
          }]
        }
      }
    };

    if (flowContent.schedule) {
      resources[`${flowContent.name}ScheduleRule`] = {
        Type: 'AWS::Events::Rule',
        Properties: {
          Name: `${flowContent.name}-schedule`,
          Description: `Schedule for ${flowContent.name}`,
          ScheduleExpression: flowContent.schedule,
          State: 'ENABLED',
          Targets: [{
            Id: `${flowContent.name}Target`,
            Arn: { 'Fn::GetAtt': [`${flowContent.name}StateMachine`, 'Arn'] },
            RoleArn: { 'Fn::GetAtt': ['EventBridgeExecutionRole', 'Arn'] },
            Input: flowContent.input ? JSON.stringify(flowContent.input) : '{}'
          }]
        }
      };
    }
  }

  const pluginsDir = path.join(process.cwd(), '.plugins');
  if (fs.existsSync(pluginsDir)) {
    const pluginDirs = fs.readdirSync(pluginsDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);

    for (const pluginDir of pluginDirs) {
      const pluginFlowsDir = path.join(pluginsDir, pluginDir, 'flows');

      if (fs.existsSync(pluginFlowsDir)) {
        const pluginFlowFiles = fs.readdirSync(pluginFlowsDir).filter(f => f.endsWith('.yml') || f.endsWith('.yaml'));
        for (const file of pluginFlowFiles) {
          const flowContent = yaml.load(fs.readFileSync(path.join(pluginFlowsDir, file), 'utf8'), { schema: cfSchema });
          if (!flowContent?.name || !flowContent?.definition) continue;

          const variables = {};

          // Handle function ARNs for plugin flows
          if (flowContent.functions) {
            flowContent.functions.forEach(func => {
              const handlerParts = func.handler.split('/');
              const functionDir = handlerParts[handlerParts.length - 2];

              const normalizedName = functionDir
                .replace(/-/g, '_')
                .replace(/[^a-zA-Z0-9_]/g, '')
                .replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
              const functionName = `lib${normalizedName.charAt(0).toUpperCase()}${normalizedName.slice(1)}`;

              variables[`${func.name}Arn`] = {
                'Fn::GetAtt': [`${functionName}`, 'Arn']
              };
            });
          }

          // Handle state machine references
          if (flowContent.stateMachineReferences) {
            flowContent.stateMachineReferences.forEach(stateMachineName => {
              variables[stateMachineName] = {
                'Fn::GetAtt': [`${stateMachineName}`, 'Arn']
              };
            });
          }

          // Get function dependencies for plugin flows
          const functionDependencies = flowContent.functions
            ? flowContent.functions.map(func => {
                const handlerParts = func.handler.split('/');
                const functionDir = handlerParts[handlerParts.length - 2];
                const normalizedName = functionDir
                  .replace(/-/g, '_')
                  .replace(/[^a-zA-Z0-9_]/g, '')
                  .replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
                return `lib${normalizedName.charAt(0).toUpperCase()}${normalizedName.slice(1)}`;
              })
            : [];

          resources[`${flowContent.name}StateMachine`] = {
            Type: 'AWS::StepFunctions::StateMachine',
            DependsOn: ['StepFunctionsExecutionRole', 'StateMachineLogGroup', ...functionDependencies],
            Properties: {
              StateMachineName: flowContent.name,
              DefinitionString: {
                'Fn::Sub': [
                  JSON.stringify(flowContent.definition),
                  variables
                ]
              },
              RoleArn: { 'Fn::GetAtt': ['StepFunctionsExecutionRole', 'Arn'] },
              LoggingConfiguration: {
                Level: 'ALL',
                IncludeExecutionData: true,
                Destinations: [{
                  CloudWatchLogsLogGroup: {
                    LogGroupArn: {
                      'Fn::Sub': 'arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:/aws/vendedlogs/states/${self:service}-${self:provider.stage}:*'
                    }
                  }
                }]
              }
            }
          };

          if (flowContent.schedule) {
            resources[`${flowContent.name}ScheduleRule`] = {
              Type: 'AWS::Events::Rule',
              Properties: {
                Name: `${flowContent.name}-schedule`,
                Description: `Schedule for ${flowContent.name}`,
                ScheduleExpression: flowContent.schedule,
                State: 'ENABLED',
                Targets: [{
                  Id: `${flowContent.name}Target`,
                  Arn: { 'Fn::GetAtt': [`${flowContent.name}StateMachine`, 'Arn'] },
                  RoleArn: { 'Fn::GetAtt': ['EventBridgeExecutionRole', 'Arn'] },
                  Input: flowContent.input ? JSON.stringify(flowContent.input) : '{}'
                }]
              }
            };
          }
        }
      }
    }
  }

  return { Resources: resources };
};