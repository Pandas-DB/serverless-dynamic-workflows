// deploy/serverless-dynamic-functions.js
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class ServerlessDynamicFunctions {
  constructor(serverless) {
    this.serverless = serverless;
    this.hooks = {
      'before:package:initialize': async () => {
        await this.downloadPlugins();
        await this.mergePluginRequirements();
        this.addDynamicFunctions();
      }
    };
  }

  async downloadPlugins() {
    const plugins = this.serverless.service.custom?.plugins?.packages || [];
    for (const pluginPath of plugins) {
      if (pluginPath.startsWith('git+')) {
        const repoName = pluginPath.split('/').pop().replace('.git', '');
        const modulePath = path.join(process.cwd(), '.plugins', repoName);

        // Create plugins directory if it doesn't exist
        fs.mkdirSync(path.join(process.cwd(), '.plugins'), { recursive: true });

        // Remove existing plugin directory if it exists
        if (fs.existsSync(modulePath)) {
          fs.rmSync(modulePath, { recursive: true });
        }

        // Clone the plugin
        const gitUrl = pluginPath.replace('git+', '');
        execSync(`git clone ${gitUrl} ${modulePath}`);

        // Create __init__.py files in plugin's functions directory
        const pluginFunctionsDir = path.join(modulePath, 'functions');
        const pluginLibDir = path.join(pluginFunctionsDir, 'lib');

        if (fs.existsSync(pluginFunctionsDir)) {
          if (!fs.existsSync(path.join(pluginFunctionsDir, '__init__.py'))) {
            fs.writeFileSync(path.join(pluginFunctionsDir, '__init__.py'), '');
          }
          if (fs.existsSync(pluginLibDir)) {
            if (!fs.existsSync(path.join(pluginLibDir, '__init__.py'))) {
              fs.writeFileSync(path.join(pluginLibDir, '__init__.py'), '');
            }
          }
        }
      }
    }
  }

  mergePluginRequirements() {
    const mainReqPath = path.join(this.serverless.config.servicePath, 'layer', 'requirements.txt');
    let requirements = new Map();

    // Read main requirements if exists
    if (fs.existsSync(mainReqPath)) {
      const content = fs.readFileSync(mainReqPath, 'utf-8');
      content.split('\n').forEach(line => {
        line = line.trim();
        if (!line || line.startsWith('#')) return;
        const [name] = line.split(/[=<>]/);
        requirements.set(name.trim().toLowerCase(), line);
      });
    }

    // Process plugin requirements
    const plugins = this.serverless.service.custom?.plugins?.packages || [];
    plugins.forEach(pluginPath => {
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
            requirements.set(name.trim().toLowerCase(), line);
          });
        }
      }
    });

    // Write merged requirements back to file
    const mergedContent = Array.from(requirements.values()).join('\n');
    fs.writeFileSync(mainReqPath, mergedContent);

    // Rebuild layer
    const layerPath = path.join(this.serverless.config.servicePath, 'layer');
    const pythonPath = path.join(layerPath, 'python', 'lib', 'python3.9', 'site-packages');
    fs.mkdirSync(pythonPath, { recursive: true });

    try {
      // First, install pyarrow with minimal dependencies
      if (Array.from(requirements.values()).some(line => line.includes('pyarrow'))) {
        execSync(`pip install --no-deps pyarrow -t ${pythonPath}`, {
          stdio: 'inherit'
        });
        // Remove pyarrow from requirements to avoid duplicate installation
        requirements.delete('pyarrow');
      }

      // Write remaining requirements back to file
      const remainingContent = Array.from(requirements.values()).join('\n');
      fs.writeFileSync(mainReqPath, remainingContent);

      // Install remaining requirements
      execSync(`pip install -r ${mainReqPath} -t ${pythonPath}`, {
        stdio: 'inherit'
      });

      this.serverless.cli.log('Successfully merged and installed requirements');
    } catch (error) {
      this.serverless.cli.log(`Warning: Failed to install requirements: ${error.message}`);
    }
  }

  normalizeFunctionName(name) {
    // Convert to camelCase and remove special characters
    return name
      .replace(/-/g, '_')
      .replace(/[^a-zA-Z0-9_]/g, '')
      .replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
  }

  truncateName(fullName) {
    if (fullName.length <= 64) return fullName;
    const hash = Math.random().toString(36).substr(2, 4);
    return `${fullName.slice(0, 30)}${hash}${fullName.slice(-30)}`;
  }

  addDynamicFunctions() {
    // First handle local functions - KEEP THIS EXACTLY AS IS
    const libDir = path.join(this.serverless.config.servicePath, 'functions', 'lib');
    this.serverless.cli.log(`Scanning for functions in: ${libDir}`);

    if (!fs.existsSync(libDir)) {
      this.serverless.cli.log('Warning: functions/lib directory does not exist');
      return;
    }

    const directories = fs.readdirSync(libDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory());

    this.serverless.cli.log(`Found ${directories.length} function directories`);

    directories.forEach(dir => {
      const dirName = dir.name;
      const normalizedName = this.normalizeFunctionName(dirName);
      const functionName = `lib${normalizedName.charAt(0).toUpperCase()}${normalizedName.slice(1)}`;

      this.serverless.cli.log(`Adding function: ${functionName} with path /lib/${dirName}`);

      const handlerPath = path.join(libDir, dirName, 'handler.py');
      if (!fs.existsSync(handlerPath)) {
        this.serverless.cli.log(`Warning: handler.py not found for ${dirName}`);
        return;
      }

      const fullName = `${this.serverless.service.service}-${this.serverless.service.provider.stage}-${functionName}`;
      const truncatedName = this.truncateName(fullName);

      this.serverless.service.functions[functionName] = {
        name: truncatedName,
        handler: `functions/lib/${dirName}/handler.handler`,
        timeout: 29,
        memorySize: 128,
        layers: [{ Ref: 'DependenciesLambdaLayer' }],
        environment: {API_USAGE_TABLE: "${self:service}-api-usage-${self:provider.stage}"},
        package: {
          patterns: [
            `functions/lib/${dirName}/**`
          ]
        },
        events: [{
          httpApi: {
            path: `/lib/${dirName}`,
            method: 'POST',
            authorizer: {
              name: 'cognitoAuthorizer'
            }
          }
        }]
      };
    });

    // Then handle plugin functions
    const plugins = this.serverless.service.custom?.plugins?.packages || [];
    plugins.forEach(pluginPath => {
      try {
        let modulePath = pluginPath;
        let repoName = '';

        if (pluginPath.startsWith('git+')) {
          repoName = pluginPath.split('/').pop().replace('.git', '');
          modulePath = path.join(process.cwd(), '.plugins', repoName);
        }

        const pluginModule = require(modulePath);
        if (typeof pluginModule.getFunctions === 'function') {
          const pluginFunctions = pluginModule.getFunctions();
          Object.entries(pluginFunctions).forEach(([name, config]) => {
            const functionName = `private${name.charAt(0).toUpperCase()}${name.slice(1)}`;
            const fullName = `${this.serverless.service.service}-${this.serverless.service.provider.stage}-${functionName}`;
            const truncatedName = this.truncateName(fullName);

            this.serverless.service.functions[functionName] = {
              ...config,
              name: truncatedName,
              layers: [{ Ref: 'DependenciesLambdaLayer' }],
              environment: {
                ...(config.environment || {}),
                PYTHONPATH: `/opt/python/lib/python3.9/site-packages:/var/task/.plugins/${repoName}`,
                API_USAGE_TABLE: "${self:service}-api-usage-${self:provider.stage}"
              },
              package: {
                patterns: [
                  ...(config.package?.patterns || []),
                  `.plugins/${repoName}/functions/**/*.py`,
                  `.plugins/${repoName}/functions/**/__init__.py`
                ]
              }
            };
          });
        }
      } catch (error) {
        this.serverless.cli.log(`Warning: Failed to load plugin ${pluginPath}: ${error.message}`);
      }
    });

    this.serverless.cli.log(`Total functions added: ${Object.keys(this.serverless.service.functions).length}`);
  }
}

module.exports = ServerlessDynamicFunctions;