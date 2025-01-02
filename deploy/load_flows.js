// deploy/load_flows.js
const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');
const { execSync } = require('child_process');

// Existing YAML types remain the same
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

const cfSchema = yaml.DEFAULT_SCHEMA.extend([getAtt, ref]);

// Add this function at the global scope so it can be used by other modules
global.loadGitPlugin = function(pluginUrl) {
  const tmpDir = path.join(process.cwd(), '.plugins');
  if (!fs.existsSync(tmpDir)) {
    fs.mkdirSync(tmpDir);
  }

  const repoName = pluginUrl.split('/').pop().replace('.git', '');
  const pluginDir = path.join(tmpDir, repoName);

  if (!fs.existsSync(pluginDir)) {
    const gitUrl = pluginUrl.replace('git+', '');
    execSync(`git clone ${gitUrl} ${pluginDir}`);
  }

  return pluginDir;
}

module.exports = (serverless) => {
  // Pre-load all git plugins
  const plugins = serverless?.service?.custom?.plugins?.packages || [];
  plugins.forEach(pluginPath => {
    if (pluginPath.startsWith('git+')) {
      const pluginDir = global.loadGitPlugin(pluginPath);
      // Add to require paths so other modules can find it
      require.main.paths.unshift(pluginDir);
    }
  });

  // Rest of your code remains exactly the same
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

  const pluginFlows = plugins.reduce((acc, pluginPath) => {
    try {
      const pluginModule = require(pluginPath.startsWith('git+') ?
        pluginPath.split('/').pop().replace('.git', '') :
        pluginPath);

      if (typeof pluginModule.deployPlugin === 'function') {
        pluginModule.deployPlugin(serverless);
      }
      if (typeof pluginModule.getFlows === 'function') {
        const additionalFlows = pluginModule.getFlows();
        Object.entries(additionalFlows).forEach(([name, content]) => {
          acc[name] = {
            name: name,
            stateMachineArn: { Ref: `${name}StateMachine` }
          };
        });
      }
    } catch (error) {
      console.warn(`Warning: Failed to load plugin ${pluginPath}: ${error.message}`);
    }
    return acc;
  }, {});

  return { ...flows, ...pluginFlows };
};