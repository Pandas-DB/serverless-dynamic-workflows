// deploy/setup-layer.js
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class LayerSetup {
  constructor(serverless) {
    this.serverless = serverless;
    this.hooks = {
      'before:package:initialize': async () => {
        await this.setupLayer();
      }
    };
  }

  async setupLayer() {
    const layerPath = path.join(this.serverless.config.servicePath, 'layer');
    const pythonPath = path.join(layerPath, 'python', 'lib', 'python3.9', 'site-packages');
    const setupScript = path.join(layerPath, 'setup-layer.sh');

    // Create setup script
    const setupContent = `#!/bin/bash

# Clean up any previous builds
rm -rf ${pythonPath}

# Create the correct directory structure
mkdir -p ${pythonPath}

# First install core dependencies that are always needed
pip install \\
    aws-lambda-powertools \\
    boto3 \\
    -t ${pythonPath} \\
    --platform manylinux2014_x86_64 \\
    --implementation cp \\
    --python-version 3.9 \\
    --only-binary=:all: \\
    --upgrade

# Now install requirements from all plugin sources
if [ -f "${layerPath}/requirements.txt" ]; then
    pip install \\
        -r ${layerPath}/requirements.txt \\
        -t ${pythonPath} \\
        --platform manylinux2014_x86_64 \\
        --implementation cp \\
        --python-version 3.9 \\
        --only-binary=:all: \\
        --upgrade
fi

# Remove unnecessary files
cd ${pythonPath}
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name "*.dist-info" -exec rm -rf {} +
find . -type d -name "*.egg-info" -exec rm -rf {} +
find . -type d -name "tests" -exec rm -rf {} +
find . -type d -name "test" -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
find . -name "*.pyd" -delete
find . -name "*.so" -exec strip {} + 2>/dev/null || true
cd ../../..
`;

    // Write setup script
    fs.writeFileSync(setupScript, setupContent);
    fs.chmodSync(setupScript, '755');

    // Merge all requirements before running setup
    await this.mergeRequirements();

    try {
      // Execute setup script
      execSync(setupScript, { stdio: 'inherit' });
      this.serverless.cli.log('Successfully built optimized layer');
    } catch (error) {
      this.serverless.cli.log(`Error building layer: ${error.message}`);
      throw error;
    }
  }

  async mergeRequirements() {
    const mainReqPath = path.join(this.serverless.config.servicePath, 'layer', 'requirements.txt');
    let requirements = new Map();

    // First read existing requirements if they exist
    if (fs.existsSync(mainReqPath)) {
      const content = fs.readFileSync(mainReqPath, 'utf-8');
      content.split('\n').forEach(line => {
        line = line.trim();
        if (!line || line.startsWith('#')) return;
        const [name] = line.split(/[=<>]/);
        requirements.set(name.trim().toLowerCase(), line);
      });
    }

    // Store original requirements before plugin processing
    const originalRequirements = new Map(requirements);

    // Process plugin requirements
    const plugins = this.serverless.service.custom?.plugins?.packages || [];
    for (const pluginPath of plugins) {
      if (pluginPath.startsWith('git+')) {
        const repoName = pluginPath.split('/').pop().replace('.git', '');
        const modulePath = path.join(process.cwd(), '.plugins', repoName);
        const pluginReqPath = path.join(modulePath, 'requirements.txt');

        if (fs.existsSync(pluginReqPath)) {
          const content = fs.readFileSync(pluginReqPath, 'utf-8');
          content.split('\n').forEach(line => {
            line = line.trim();
            if (!line || line.startsWith('#')) return;
            const [name] = line.split(/[=<>]/);
            // Plugin requirements override existing ones
            requirements.set(name.trim().toLowerCase(), line);
          });
        }
      }
    }

    // Restore non-conflicting original requirements
    originalRequirements.forEach((line, name) => {
      if (!requirements.has(name)) {
        requirements.set(name, line);
      }
    });

    // Write merged requirements
    const mergedContent = Array.from(requirements.values()).join('\n');
    fs.writeFileSync(mainReqPath, mergedContent);
  }
}

module.exports = LayerSetup;