#!/usr/bin/env python3
import os
import sys
import json
import subprocess
from pathlib import Path


def create_plugin_structure(target_dir: str = 'private-workflows'):
    target_dir = Path(target_dir)

    # Create base directory structure
    dirs = [
        '',
        'flows',
        'functions/lib',
        'tests/functions-lib'
    ]

    for dir_path in dirs:
        (target_dir / dir_path).mkdir(parents=True, exist_ok=True)

    # Create index.js content
    index_content = '''const fs = require('fs');
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
          handler: `functions/lib/${dir}/handler.handler`,
          events: [{
            httpApi: {
              path: `/lib/${dir}`,
              method: 'POST',
              authorizer: {
                name: 'cognitoAuthorizer'
              }
            }
          }],
          package: {
            patterns: [`functions/lib/${dir}/**`]
          },
          layers: [{ Ref: 'DependenciesLambdaLayer' }],
          environment: {
            API_USAGE_TABLE: "${self:service}-api-usage-${self:provider.stage}"
          }
        };
      });
    }

    return functions;
  }
};'''

    # Create package.json content
    package_content = {
        "name": target_dir.name,
        "version": "1.0.0",
        "private": True,
        "main": "index.js",
        "dependencies": {
            "js-yaml": "^4.1.0"
        }
    }

    # Create .gitignore content
    gitignore_content = '''__pycache__/
*.pyc
.pytest_cache/
.DS_Store
node_modules/'''

    # Create example function content
    example_function_content = '''import json

def handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Hello from private function!'})
    }'''

    # Create example test content
    example_test_content = '''import pytest
import json
from functions.lib.example_function.handler import handler

def test_handler():
    response = handler({}, {})
    assert response['statusCode'] == 200
    assert 'message' in json.loads(response['body'])'''

    # Write files
    (target_dir / 'index.js').write_text(index_content)
    (target_dir / 'package.json').write_text(json.dumps(package_content, indent=2))
    (target_dir / '.gitignore').write_text(gitignore_content)

    # Create example function
    example_func_dir = target_dir / 'functions/lib/example_function'
    example_func_dir.mkdir(parents=True, exist_ok=True)
    (example_func_dir / 'handler.py').write_text(example_function_content)
    (example_func_dir / '__init__.py').touch()

    # Create example test
    (target_dir / 'tests/functions-lib/test_example_function.py').write_text(example_test_content)

    # Initialize git repo
    subprocess.run(['git', 'init'], cwd=target_dir)

    print(f'''
Private plugin repository created at: {target_dir}

Next steps:
1. cd {target_dir}
2. npm install
3. Add your private functions in functions/lib/
4. Add your private flows in flows/
5. Add your tests in tests/functions-lib/
6. Create GitHub repository and push your code
7. Add the repository to your main project's config.json:
   {{
     "plugins": [
       "git+https://YOUR_TOKEN@github.com/your-org/{target_dir.name}.git"
     ]
   }}
''')


if __name__ == '__main__':
    print('Get sure you allow it to create folders in your system "chmod +x scripts/create-private-plugin.py"')
    target_dir = sys.argv[1] if len(sys.argv) > 1 else 'private-workflows'
    create_plugin_structure(target_dir)