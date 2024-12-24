// deploy/load_flows.js
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

// Custom YAML type for handling CloudFormation intrinsic functions
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

// Create a custom schema
const cfSchema = yaml.DEFAULT_SCHEMA.extend([getAtt, ref]);

module.exports = () => {
  const flowsDir = path.join(__dirname, '..', 'flows');
  const flowFiles = fs.readdirSync(flowsDir).filter(file =>
    file.endsWith('.yml') || file.endsWith('.yaml')
  );

  const flows = {};
  flowFiles.forEach(file => {
    const flowContent = yaml.load(
      fs.readFileSync(path.join(flowsDir, file), 'utf8'),
      { schema: cfSchema }
    );
    flows[flowContent.name] = {
      name: flowContent.name,
      stateMachineArn: { Ref: `${flowContent.name}StateMachine` }
    };
  });

  return flows;
};