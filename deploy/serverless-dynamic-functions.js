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

  addDynamicFunctions() {
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
      // Normalize the function name for CloudFormation compatibility
      const normalizedName = this.normalizeFunctionName(dirName);
      const functionName = `lib${normalizedName.charAt(0).toUpperCase()}${normalizedName.slice(1)}`;

      this.serverless.cli.log(`Adding function: ${functionName} with path /lib/${dirName}`);

      // Verify handler file exists
      const handlerPath = path.join(libDir, dirName, 'handler.py');
      if (!fs.existsSync(handlerPath)) {
        this.serverless.cli.log(`Warning: handler.py not found for ${dirName}`);
        return;
      }

      // Define the function with proper naming
      this.serverless.service.functions[functionName] = {
        name: `${this.serverless.service.service}-${this.serverless.service.provider.stage}-${functionName}`,
        handler: `functions/lib/${dirName}/handler.handler`,
        timeout: 29, // Set to 29 to avoid API Gateway 30s timeout warning
        memorySize: 128,
        layers: [{ Ref: 'DependenciesLambdaLayer' }],
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

    // Log the final function count
    this.serverless.cli.log(`Total functions added: ${Object.keys(this.serverless.service.functions).length}`);
  }
}

module.exports = ServerlessDynamicFunctions;