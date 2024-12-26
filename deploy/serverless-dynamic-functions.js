// deploy/serverless_dynamic_functions.js
const fs = require('fs');
const path = require('path');

class ServerlessDynamicFunctions {
  constructor(serverless) {
    this.serverless = serverless;

    this.hooks = {
      'before:package:initialize': this.addDynamicFunctions.bind(this)
    };
  }

  addDynamicFunctions() {
    const libDir = path.join(__dirname, 'functions', 'lib');

    if (!fs.existsSync(libDir)) {
      this.serverless.cli.log('Warning: functions/lib directory does not exist');
      return;
    }

    const directories = fs.readdirSync(libDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory());

    directories.forEach(dir => {
      const name = dir.name;
      const functionName = name.replace(/_([a-z])/g, g => g[1].toUpperCase());

      this.serverless.service.functions[functionName] = {
        handler: `functions/lib/${name}/handler.handler`,
        timeout: 30,
        memorySize: 128,
        layers: [{ Ref: 'DependenciesLambdaLayer' }],
        events: [{
          httpApi: {
            path: `/lib/${name.replace(/_/g, '-')}`,  // Added /lib/ prefix here
            method: 'POST',
            authorizer: {
              name: 'cognitoAuthorizer'
            }
          }
        }]
      };
    });
  }
}

module.exports = ServerlessDynamicFunctions;