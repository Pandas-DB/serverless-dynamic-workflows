const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const JSZip = require('jszip');

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

const createZip = async (handlerCode, handlerName) => {
  const zip = new JSZip();
  zip.file(`${handlerName}.py`, handlerCode);
  return zip.generateAsync({ type: 'base64' });
};

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
      ManagedPolicyArns: ['arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'],
      Policies: [{
        PolicyName: 'StepFunctionsExecutionPolicy',
        PolicyDocument: {
          Version: '2012-10-17',
          Statement: [{
            Effect: 'Allow',
            Action: ['lambda:InvokeFunction'],
            Resource: '*'
          }]
        }
      }]
    }
  };

  const flowsDir = path.join(__dirname, '..', 'flows');
  const flowFiles = fs.readdirSync(flowsDir).filter(f => f.endsWith('.yml') || f.endsWith('.yaml'));

  for (const file of flowFiles) {
    const flowContent = yaml.load(fs.readFileSync(path.join(flowsDir, file), 'utf8'), { schema: cfSchema });
    if (!flowContent?.name || !flowContent?.definition) continue;

    if (flowContent.functions) {
      for (const func of flowContent.functions) {
        const [handlerPath] = func.handler.split('.');
        const sourceFile = handlerPath.replace('scripts/', '') + '.py';
        const sourcePath = path.join(__dirname, '..', 'scripts', sourceFile);
        const handlerName = sourceFile.replace('.py', '');

        try {
          const sourceCode = fs.readFileSync(sourcePath, 'utf8');
          const zipContent = await createZip(sourceCode, handlerName);

          resources[func.name] = {
            Type: 'AWS::Lambda::Function',
            Properties: {
              FunctionName: func.name,
              Handler: `${handlerName}.handler`,
              Runtime: func.runtime || 'python3.9',
              Code: { ZipFile: zipContent },
              Role: { 'Fn::GetAtt': ['IamRoleLambdaExecution', 'Arn'] }
            }
          };
        } catch (error) {
          console.error(`Error processing function ${func.name}:`, error);
          continue;
        }
      }
    }

    const variables = {};
    if (flowContent.functions) {
      flowContent.functions.forEach(func => {
        variables[`${func.name}Arn`] = { 'Fn::GetAtt': [func.name, 'Arn'] };
      });
    }

    resources[`${flowContent.name}StateMachine`] = {
      Type: 'AWS::StepFunctions::StateMachine',
      DependsOn: ['StepFunctionsExecutionRole']
        .concat(flowContent.functions?.map(f => f.name) || []),
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
  }

  return { Resources: resources };
};