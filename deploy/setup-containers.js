// deploy/setup-containers.js
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const AWS = require('aws-sdk');

class ContainerSetup {
 constructor(serverless) {
   this.serverless = serverless;
   this.hooks = {
     'before:package:initialize': async () => {
       await this.setupECR();
       await this.setupContainers();
     }
   };
 }

 async setupECR() {
   const region = this.serverless.service.provider.region;
   const serviceName = this.serverless.service.service;

   try {
     // Configure AWS SDK
     const ecr = new AWS.ECR({ region });

     // Get AWS account ID
     const sts = new AWS.STS();
     const { Account: accountId } = await sts.getCallerIdentity().promise();

     // Try to authenticate with ECR
     try {
       this.serverless.cli.log('Authenticating with ECR...');
       execSync(`aws ecr get-login-password --region ${region} | docker login --username AWS --password-stdin ${accountId}.dkr.ecr.${region}.amazonaws.com`);
     } catch (error) {
       this.serverless.cli.log('Error authenticating with ECR:', error.message);
       throw error;
     }

     // Create repositories if they don't exist
     const repositories = ['baseimage', 'heavyimage'];
     for (const repo of repositories) {
       const repoName = `${serviceName}/${repo}`;
       try {
         await ecr.describeRepositories({
           repositoryNames: [repoName]
         }).promise();
         this.serverless.cli.log(`Repository ${repoName} already exists`);
       } catch (error) {
         if (error.code === 'RepositoryNotFoundException') {
           this.serverless.cli.log(`Creating repository ${repoName}...`);
           await ecr.createRepository({
             repositoryName: repoName
           }).promise();
           this.serverless.cli.log(`Repository ${repoName} created successfully`);
         } else {
           this.serverless.cli.log('Error checking/creating ECR repository:', error.message);
           throw error;
         }
       }
     }
   } catch (error) {
     this.serverless.cli.log('Error setting up ECR:', error.message);
     throw error;
   }
 }

 async setupContainers() {
   // Create base Dockerfile with minimal dependencies
   const baseDockerfile = `FROM public.ecr.aws/lambda/python:3.9

# Install core dependencies
COPY layer/requirements-base.txt .
RUN pip install -r requirements-base.txt

# Copy function code
COPY functions/ ./functions/

# Create necessary __init__.py files
RUN find functions -type d -exec touch {}/__init__.py \\;

CMD ["handler.handler"]`;

   // Create heavy Dockerfile with all dependencies
   const heavyDockerfile = `FROM public.ecr.aws/lambda/python:3.9

# Copy and install all requirements
COPY layer/requirements.txt .
RUN pip install -r requirements.txt

# Copy function code and plugins
COPY functions/ ./functions/
COPY .plugins/ ./.plugins/

# Create necessary __init__.py files
RUN find functions .plugins -type d -exec touch {}/__init__.py \\;

CMD ["handler.handler"]`;

   // Write Dockerfiles
   fs.writeFileSync('Dockerfile.base', baseDockerfile);
   fs.writeFileSync('Dockerfile.heavy', heavyDockerfile);

   // Create requirements-base.txt with minimal dependencies
   const baseRequirements = `aws-lambda-powertools
boto3`;

   const layerPath = path.join(this.serverless.config.servicePath, 'layer');
   fs.mkdirSync(layerPath, { recursive: true });
   fs.writeFileSync(path.join(layerPath, 'requirements-base.txt'), baseRequirements);

   // Merge plugin requirements
   await this.mergeRequirements();
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

   // Add base requirements to the heavy image requirements
   const baseReqPath = path.join(this.serverless.config.servicePath, 'layer', 'requirements-base.txt');
   if (fs.existsSync(baseReqPath)) {
     const content = fs.readFileSync(baseReqPath, 'utf-8');
     content.split('\n').forEach(line => {
       line = line.trim();
       if (!line || line.startsWith('#')) return;
       const [name] = line.split(/[=<>]/);
       requirements.set(name.trim().toLowerCase(), line);
     });
   }

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

   this.serverless.cli.log('Successfully created container configurations');
 }
}

module.exports = ContainerSetup;