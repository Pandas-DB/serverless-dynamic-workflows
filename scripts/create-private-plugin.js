#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const targetDir = process.argv[2] || 'private-workflows';

// Create base directory structure
const dirs = [
  '',
  'flows',
  'functions/lib',
  'tests/functions-lib'
];

dirs.forEach(dir => {
  fs.mkdirSync(path.join(targetDir, dir), { recursive: true });
});

// Create index.js
const indexContent = `const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

module.exports = {
  getFlows() {
    const flowsDir = path.join(__dirname, 'flows');
    const flows = {};

    if (fs.existsSync(flowsDir)) {
      const flowFiles = fs.readdirSync(flowsDir)
        .filter(file => file.endsWith('.yml'));

      flowFiles.forEach(file => {
        const flowPath = path.join(flowsDir, file);
        const flowContent = yaml.load(fs.readFileSync(flowPath, 'utf8'));
        flows[flowContent.name] = flowContent;
      });
    }

    return flows;
  },

  getFunctions() {
    const libDir = path.join(__dirname, 'functions', 'lib');
    const functions = {};

    if (fs.existsSync(libDir)) {
      const functionDirs = fs.readdirSync(libDir);
      functionDirs.forEach(dir => {
        if (!fs.statSync(path.join(libDir, dir)).isDirectory()) return;

        functions[dir] = {
          handler: \`functions/lib/\${dir}/handler.handler\`,
          events: [{
            httpApi: {
              path: \`/lib/\${dir}\`,
              method: 'POST',
              authorizer: {
                name: 'cognitoAuthorizer'
              }
            }
          }],
          package: {
            patterns: [\`functions/lib/\${dir}/**\`]
          },
          layers: [{ Ref: 'DependenciesLambdaLayer' }],
          environment: {
            API_USAGE_TABLE: "\${self:service}-api-usage-\${self:provider.stage}"
          }
        };
      });
    }

    return functions;
  }
};`;

// Create package.json
const packageContent = {
  "name": path.basename(targetDir),
  "version": "1.0.0",
  "private": true,
  "main": "index.js",
  "dependencies": {
    "js-yaml": "^4.1.0"
  }
};

// Create .gitignore
const gitignoreContent = `__pycache__/
*.pyc
.pytest_cache/
.DS_Store
node_modules/`;

// Create example function
const exampleFunctionContent = `import json

def handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Hello from private function!'})
    }`;

const exampleInitContent = ``;

// Write files
fs.writeFileSync(path.join(targetDir, 'index.js'), indexContent);
fs.writeFileSync(path.join(targetDir, 'package.json'), JSON.stringify(packageContent, null, 2));
fs.writeFileSync(path.join(targetDir, '.gitignore'), gitignoreContent);

// Create example function
const exampleFuncDir = path.join(targetDir, 'functions/lib/example_function');
fs.mkdirSync(exampleFuncDir, { recursive: true });
fs.writeFileSync(path.join(exampleFuncDir, 'handler.py'), exampleFunctionContent);
fs.writeFileSync(path.join(exampleFuncDir, '__init__.py'), exampleInitContent);

// Create example test
const exampleTestContent = `import pytest
from functions.lib.example_function.handler import handler

def test_handler():
    response = handler({}, {})
    assert response['statusCode'] == 200
    assert 'message' in json.loads(response['body'])`;

fs.writeFileSync(
  path.join(targetDir, 'tests/functions-lib/test_example_function.py'),
  exampleTestContent
);

// Initialize git repo
execSync('git init', { cwd: targetDir });

console.log(`
Private plugin repository created at: ${targetDir}

Next steps:
1. cd ${targetDir}
2. npm install
3. Add your private functions in functions/lib/
4. Add your private flows in flows/
5. Add your tests in tests/functions-lib/
6. Create GitHub repository and push your code
7. Add the repository to your main project's config.json:
   {
     "plugins": [
       "git+https://YOUR_TOKEN@github.com/your-org/${targetDir}.git"
     ]
   }
`);