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
    index_content = '''// index.js
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

function checkFileConflict(sourcePath, targetPath, fileName) {
  if (fs.existsSync(targetPath) && !fileName.endsWith('requirements.txt')) {
    throw new Error(`Conflict: File ${fileName} already exists in target path ${targetPath}`);
  }
}

function copyDirectory(source, target, exclude = []) {
  if (!fs.existsSync(target)) {
    fs.mkdirSync(target, { recursive: true });
  }

  const files = fs.readdirSync(source);
  files.forEach(file => {
    if (exclude.some(pattern => file.includes(pattern))) {
      return;
    }

    const sourcePath = path.join(source, file);
    const targetPath = path.join(target, file);
    const stat = fs.statSync(sourcePath);

    if (stat.isDirectory()) {
      copyDirectory(sourcePath, targetPath, exclude);
    } else {
      checkFileConflict(sourcePath, targetPath, file);
      fs.copyFileSync(sourcePath, targetPath);
    }
  });
}

function mergeRequirements(privateReqs, publicReqsPath) {
  let requirements = new Set();

  if (fs.existsSync(privateReqs)) {
    const privateContent = fs.readFileSync(privateReqs, 'utf8');
    privateContent.split('\n').forEach(line => {
      if (line.trim()) requirements.add(line.trim());
    });
  }

  if (fs.existsSync(publicReqsPath)) {
    const publicContent = fs.readFileSync(publicReqsPath, 'utf8');
    publicContent.split('\n').forEach(line => {
      const req = line.trim();
      if (req && !requirements.has(req)) {
        requirements.add(req);
      }
    });
  }

  return Array.from(requirements).join('\n');
}

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
    const repoName = path.basename(__dirname);

    if (fs.existsSync(libDir)) {
      const functionDirs = fs.readdirSync(libDir);
      functionDirs.forEach(dir => {
        const functionPath = path.join(libDir, dir);
        if (fs.statSync(functionPath).isDirectory()) {
          const functionName = `lib${dir.charAt(0).toUpperCase() + dir.slice(1)}`;
          functions[functionName] = {
            handler: `functions/lib/${dir}/handler.handler`,  // Keep original format, no .plugins prefix
            events: [
              {
                httpApi: {
                  path: `/lib/${dir}`,
                  method: 'POST',
                  authorizer: {
                    name: 'cognitoAuthorizer'
                  }
                }
              }
            ],
            package: {
              patterns: [`functions/lib/${dir}/**`]
            },
          };
        }
      });
    }

    return functions;
  },

  deployPlugin(serverless) {
    const publicRoot = path.join(process.cwd());
    const excludePatterns = ['__pycache__', '.pyc'];

    // Copy functions/lib
    const sourceLibDir = path.join(__dirname, 'functions', 'lib');
    const targetLibDir = path.join(publicRoot, 'functions', 'lib');
    if (fs.existsSync(sourceLibDir)) {
      copyDirectory(sourceLibDir, targetLibDir, excludePatterns);
    }

    // Copy tests
    const sourceTestsDir = path.join(__dirname, 'tests');
    const targetTestsDir = path.join(publicRoot, 'test');
    if (fs.existsSync(sourceTestsDir)) {
      copyDirectory(sourceTestsDir, targetTestsDir, excludePatterns);
    }

    // Merge requirements.txt
    const privateReqs = path.join(__dirname, 'requirements.txt');
    const publicReqs = path.join(publicRoot, 'requirements.txt');
    const mergedContent = mergeRequirements(privateReqs, publicReqs);
    fs.writeFileSync(publicReqs, mergedContent);

    // Register functions with serverless-dynamic-functions
    const pluginFunctions = this.getFunctions();
    if (serverless.service.functions) {
      Object.assign(serverless.service.functions, pluginFunctions);
    } else {
      serverless.service.functions = pluginFunctions;
    }
  }
};
    '''

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

    # Create an empty requirements.txt file
    (target_dir / 'requirements.txt').write_text('')

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
