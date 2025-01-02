// deploy/serverless-dynamic-functions.js
const fs = require('fs');
const path = require('path');

class ServerlessDynamicFunctions {
  constructor(serverless) {
    this.serverless = serverless;
    this.hooks = {
      'before:package:initialize': this.addDynamicFunctions.bind(this)
    };
  }

  normalizeFunctionName(name) {
    // Convert to camelCase and remove special characters
    return name
      .replace(/-/g, '_')
      .replace(/[^a-zA-Z0-9_]/g, '')
      .replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
  }

  // New helper function to ensure name is within 64-char limit
  truncateName(fullName) {
    if (fullName.length <= 64) return fullName;

    // Take first 30 chars and last 30 chars with a 4-char hash in between
    const hash = Math.random().toString(36).substr(2, 4);
    return `${fullName.slice(0, 30)}${hash}${fullName.slice(-30)}`;
  }

  addDynamicFunctions() {
    // First handle local functions
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
        if (pluginPath.startsWith('git+')) {
          const repoName = pluginPath.split('/').pop().replace('.git', '');
          modulePath = path.join(process.cwd(), '.plugins', repoName);

          // Clone if not exists
          if (!fs.existsSync(modulePath)) {
            const { execSync } = require('child_process');
            const gitUrl = pluginPath.replace('git+', '');
            fs.mkdirSync(path.join(process.cwd(), '.plugins'), { recursive: true });
            execSync(`git clone ${gitUrl} ${modulePath}`);
          }
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
              name: truncatedName
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