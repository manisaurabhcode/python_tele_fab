import React, { useState } from 'react';
import { Upload, Download, FileText, Settings, CheckCircle, AlertCircle } from 'lucide-react';

const ApigeeKongMigrator = () => {
  const [apigeeXml, setApigeeXml] = useState('');
  const [kongYaml, setKongYaml] = useState('');
  const [customPlugins, setCustomPlugins] = useState([]);
  const [proxyCode, setProxyCode] = useState('');
  const [migrationLog, setMigrationLog] = useState([]);
  const [activeTab, setActiveTab] = useState('upload');

  // Policy mapping configuration
  const policyMappings = {
    'SpikeArrest': { plugin: 'rate-limiting', bundled: true },
    'Quota': { plugin: 'rate-limiting', bundled: true },
    'VerifyAPIKey': { plugin: 'key-auth', bundled: true },
    'OAuthV2': { plugin: 'oauth2', bundled: true },
    'JSONThreatProtection': { plugin: 'custom-json-threat', bundled: false },
    'XMLThreatProtection': { plugin: 'custom-xml-threat', bundled: false },
    'AssignMessage': { plugin: 'request-transformer', bundled: true },
    'ExtractVariables': { plugin: 'custom-extract-vars', bundled: false },
    'RaiseFault': { plugin: 'request-termination', bundled: true },
    'ServiceCallout': { plugin: 'custom-service-callout', bundled: false },
    'JavaScript': { plugin: 'custom-js-executor', bundled: false },
    'BasicAuthentication': { plugin: 'basic-auth', bundled: true },
    'CORS': { plugin: 'cors', bundled: true },
    'Statistics': { plugin: 'prometheus', bundled: true },
    'MessageLogging': { plugin: 'file-log', bundled: true }
  };

  const parseApigeeXml = (xml) => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xml, 'text/xml');
    
    const policies = [];
    const steps = doc.querySelectorAll('Step');
    
    steps.forEach(step => {
      const name = step.querySelector('Name')?.textContent;
      const condition = step.querySelector('Condition')?.textContent;
      
      if (name) {
        const policyRef = doc.querySelector(`[name="${name}"]`);
        if (policyRef) {
          const policyType = policyRef.tagName;
          policies.push({
            name,
            type: policyType,
            condition,
            config: extractPolicyConfig(policyRef)
          });
        }
      }
    });
    
    return policies;
  };

  const extractPolicyConfig = (policyNode) => {
    const config = {};
    Array.from(policyNode.children).forEach(child => {
      if (child.textContent && child.children.length === 0) {
        config[child.tagName] = child.textContent;
      }
    });
    return config;
  };

  const generateKongYaml = (policies) => {
    const kongServices = [];
    const kongPlugins = [];
    const customPluginsList = [];
    
    policies.forEach((policy, idx) => {
      const mapping = policyMappings[policy.type];
      
      if (mapping) {
        const pluginConfig = {
          name: mapping.plugin,
          enabled: true,
          config: mapPolicyConfig(policy)
        };
        
        if (!mapping.bundled) {
          customPluginsList.push({
            name: mapping.plugin,
            schema: generatePluginSchema(policy)
          });
        }
        
        kongPlugins.push(pluginConfig);
      }
    });
    
    setCustomPlugins(customPluginsList);
    
    const yaml = `_format_version: "3.0"

services:
  - name: migrated-service
    url: http://backend-api:8080
    routes:
      - name: migrated-route
        paths:
          - /api/v1
        methods:
          - GET
          - POST
          - PUT
          - DELETE
    plugins:
${kongPlugins.map(p => `      - name: ${p.name}
        enabled: ${p.enabled}
        config:
${Object.entries(p.config).map(([k, v]) => `          ${k}: ${JSON.stringify(v)}`).join('\n')}`).join('\n')}

plugins:
${kongPlugins.map((p, i) => `  - name: ${p.name}
    id: plugin-${i}
    enabled: true
    config:
${Object.entries(p.config).map(([k, v]) => `      ${k}: ${JSON.stringify(v)}`).join('\n')}`).join('\n')}
`;
    
    return yaml;
  };

  const mapPolicyConfig = (policy) => {
    const config = {};
    
    switch (policy.type) {
      case 'SpikeArrest':
        config.second = parseInt(policy.config.Rate?.split('/')[0]) || 10;
        break;
      case 'Quota':
        config.second = parseInt(policy.config.Allow?.split('/')[0]) || 100;
        break;
      case 'VerifyAPIKey':
        config.key_names = ['apikey'];
        config.hide_credentials = true;
        break;
      case 'CORS':
        config.origins = ['*'];
        config.methods = ['GET', 'POST', 'PUT', 'DELETE'];
        config.headers = ['Accept', 'Content-Type', 'Authorization'];
        config.credentials = true;
        break;
      case 'AssignMessage':
        config.add = { headers: [] };
        config.remove = { headers: [] };
        break;
      default:
        config.enabled = true;
    }
    
    return config;
  };

  const generatePluginSchema = (policy) => {
    return {
      name: policyMappings[policy.type].plugin,
      fields: [
        { config: { type: 'record', fields: [{ enabled: { type: 'boolean', default: true } }] } }
      ]
    };
  };

  const generateCustomPluginCode = (plugin) => {
    return `-- Custom Kong Plugin: ${plugin.name}
local plugin = {
  PRIORITY = 1000,
  VERSION = "1.0.0",
}

function plugin:access(conf)
  kong.log.debug("Executing custom plugin: ${plugin.name}")
  
  -- Add your custom logic here
  -- This is a placeholder implementation
  
  local headers = kong.request.get_headers()
  kong.log.info("Processing request with headers: ", headers)
  
  -- Example: Add custom header
  kong.service.request.set_header("X-Custom-Plugin", "${plugin.name}")
end

return plugin
`;
  };

  const generateProxyTestCode = () => {
    return `// Express.js Test Proxy for Kong Migration
const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

// Kong Gateway URL
const KONG_GATEWAY = process.env.KONG_GATEWAY || 'http://localhost:8000';

// Test endpoint that routes through Kong
app.all('/test/*', async (req, res) => {
  try {
    const path = req.params[0];
    const kongUrl = \`\${KONG_GATEWAY}/api/v1/\${path}\`;
    
    const response = await axios({
      method: req.method,
      url: kongUrl,
      headers: {
        ...req.headers,
        host: undefined // Remove host header
      },
      data: req.body,
      validateStatus: () => true
    });
    
    res.status(response.status).json({
      kongResponse: response.data,
      kongHeaders: response.headers,
      statusCode: response.status
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(\`Test proxy running on port \${PORT}\`);
  console.log(\`Kong Gateway: \${KONG_GATEWAY}\`);
});
`;
  };

  const generateDeploymentInstructions = () => {
    return `# Apigee to Kong Migration - Deployment Instructions

## Prerequisites
- Kong Gateway 3.x installed
- decK CLI tool installed (\`brew install deck\` or download from Kong)
- Access to Kong Admin API
- Docker (optional, for custom plugins)

## Step 1: Review Generated Files
1. \`kong-config.yaml\` - Main Kong configuration
2. \`custom-plugins/\` - Custom plugin implementations
3. \`test-proxy.js\` - Test proxy server

## Step 2: Install Custom Plugins

### Option A: Using Docker
\`\`\`bash
# Build custom plugin image
docker build -t kong-custom-plugins:latest -f Dockerfile.plugins .

# Run Kong with custom plugins
docker run -d \\
  --name kong-gateway \\
  -e "KONG_DATABASE=off" \\
  -e "KONG_DECLARATIVE_CONFIG=/kong/kong-config.yaml" \\
  -e "KONG_PLUGINS=bundled,${customPlugins.map(p => p.name).join(',')}" \\
  -v \$(pwd)/kong-config.yaml:/kong/kong-config.yaml \\
  -v \$(pwd)/custom-plugins:/usr/local/share/lua/5.1/kong/plugins \\
  -p 8000:8000 \\
  -p 8001:8001 \\
  kong-custom-plugins:latest
\`\`\`

### Option B: Manual Installation
\`\`\`bash
# Copy custom plugins to Kong plugins directory
sudo cp -r custom-plugins/* /usr/local/share/lua/5.1/kong/plugins/

# Update Kong configuration
sudo nano /etc/kong/kong.conf
# Add: plugins = bundled,${customPlugins.map(p => p.name).join(',')}

# Restart Kong
sudo kong restart
\`\`\`

## Step 3: Validate Configuration
\`\`\`bash
# Validate the Kong configuration
deck validate --state kong-config.yaml

# Check for syntax errors
deck dump --output-file current-config.yaml
\`\`\`

## Step 4: Deploy Configuration
\`\`\`bash
# Deploy to Kong (DB-less mode)
deck sync --state kong-config.yaml

# Or with Kong running with database
deck sync --state kong-config.yaml --kong-addr http://localhost:8001
\`\`\`

## Step 5: Test the Migration
\`\`\`bash
# Start test proxy
node test-proxy.js

# Test endpoint
curl -X GET http://localhost:3000/test/resource \\
  -H "apikey: your-api-key"

# Check Kong metrics
curl http://localhost:8001/status
\`\`\`

## Step 6: Monitor and Validate
\`\`\`bash
# View Kong logs
tail -f /usr/local/kong/logs/error.log

# Test rate limiting
for i in {1..20}; do
  curl http://localhost:8000/api/v1/test
done

# Verify plugin execution
curl http://localhost:8001/plugins
\`\`\`

## Rollback Procedure
\`\`\`bash
# Export current configuration
deck dump --output-file backup-config.yaml

# Restore previous configuration
deck sync --state backup-config.yaml
\`\`\`

## Troubleshooting
1. **Plugin not loading**: Check Kong logs for Lua errors
2. **Rate limiting not working**: Verify plugin configuration
3. **Custom plugin errors**: Ensure plugin files are in correct directory

## Integration Function for Existing Code
Add this function to your existing codebase:

\`\`\`javascript
const migrateApigeeToKong = async (apigeeXmlPath, kongOutputPath) => {
  const fs = require('fs').promises;
  
  // Read Apigee shared flow XML
  const apigeeXml = await fs.readFile(apigeeXmlPath, 'utf-8');
  
  // Parse and convert (use the logic from the tool)
  const policies = parseApigeeXml(apigeeXml);
  const kongYaml = generateKongYaml(policies);
  
  // Write Kong configuration
  await fs.writeFile(kongOutputPath, kongYaml);
  
  // Write custom plugins
  for (const plugin of customPlugins) {
    const pluginCode = generateCustomPluginCode(plugin);
    await fs.writeFile(
      \`custom-plugins/\${plugin.name}/handler.lua\`,
      pluginCode
    );
  }
  
  // Write test proxy
  const proxyCode = generateProxyTestCode();
  await fs.writeFile('test-proxy.js', proxyCode);
  
  return {
    kongConfig: kongOutputPath,
    customPlugins: customPlugins.length,
    testProxy: 'test-proxy.js'
  };
};

// Usage in your route
app.post('/api/migrate', async (req, res) => {
  try {
    const result = await migrateApigeeToKong(
      req.body.apigeeXmlPath,
      'kong-config.yaml'
    );
    res.json({ success: true, ...result });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
\`\`\`

## Production Checklist
- [ ] Review all generated policies
- [ ] Test custom plugins thoroughly
- [ ] Configure proper rate limits
- [ ] Set up monitoring and alerting
- [ ] Document API changes
- [ ] Update client applications
- [ ] Plan rollback strategy
`;
  };

  const handleApigeeUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const xml = event.target.result;
        setApigeeXml(xml);
        processApigeeXml(xml);
      };
      reader.readAsText(file);
    }
  };

  const processApigeeXml = (xml) => {
    try {
      addLog('Parsing Apigee shared flow...', 'info');
      const policies = parseApigeeXml(xml);
      addLog(`Found ${policies.length} policies`, 'success');
      
      addLog('Generating Kong configuration...', 'info');
      const yaml = generateKongYaml(policies);
      setKongYaml(yaml);
      addLog('Kong YAML generated successfully', 'success');
      
      const proxy = generateProxyTestCode();
      setProxyCode(proxy);
      addLog('Test proxy code generated', 'success');
      
      addLog(`Generated ${customPlugins.length} custom plugins`, 'info');
      setActiveTab('output');
    } catch (error) {
      addLog(`Error: ${error.message}`, 'error');
    }
  };

  const addLog = (message, type) => {
    setMigrationLog(prev => [...prev, { message, type, timestamp: new Date().toISOString() }]);
  };

  const downloadFile = (content, filename) => {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadAll = () => {
    downloadFile(kongYaml, 'kong-config.yaml');
    downloadFile(proxyCode, 'test-proxy.js');
    downloadFile(generateDeploymentInstructions(), 'DEPLOYMENT.md');
    
    customPlugins.forEach(plugin => {
      downloadFile(generateCustomPluginCode(plugin), `${plugin.name}-handler.lua`);
    });
    
    addLog('All files downloaded', 'success');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="flex items-center gap-3 mb-8">
            <Settings className="w-10 h-10 text-indigo-600" />
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Apigee to Kong Migration Tool</h1>
              <p className="text-gray-600">Convert Apigee shared flows to Kong Gateway configuration</p>
            </div>
          </div>

          <div className="flex gap-4 mb-6 border-b">
            {['upload', 'output', 'plugins', 'logs'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 font-medium transition ${
                  activeTab === tab
                    ? 'text-indigo-600 border-b-2 border-indigo-600'
                    : 'text-gray-600 hover:text-indigo-600'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {activeTab === 'upload' && (
            <div className="space-y-6">
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-indigo-500 transition">
                <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <p className="text-lg font-medium text-gray-700 mb-2">Upload Apigee Shared Flow XML</p>
                <p className="text-sm text-gray-500 mb-4">Select your Apigee proxy bundle or shared flow XML file</p>
                <input
                  type="file"
                  accept=".xml"
                  onChange={handleApigeeUpload}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 mx-auto"
                />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="font-semibold text-blue-900 mb-2">Sample Apigee XML</h3>
                <pre className="text-xs bg-white p-3 rounded overflow-x-auto">
{`<?xml version="1.0" encoding="UTF-8"?>
<SharedFlow name="security-flow">
  <Flows>
    <Flow name="security-checks">
      <Request>
        <Step>
          <Name>Verify-API-Key</Name>
        </Step>
        <Step>
          <Name>Spike-Arrest</Name>
        </Step>
      </Request>
    </Flow>
  </Flows>
</SharedFlow>`}
                </pre>
              </div>
            </div>
          )}

          {activeTab === 'output' && (
            <div className="space-y-6">
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-lg font-semibold text-gray-900">Kong Configuration (decK YAML)</h3>
                  <button
                    onClick={() => downloadFile(kongYaml, 'kong-config.yaml')}
                    className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                </div>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm max-h-96">
                  {kongYaml || 'Upload Apigee XML to generate Kong configuration'}
                </pre>
              </div>

              <div>
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-lg font-semibold text-gray-900">Test Proxy Code</h3>
                  <button
                    onClick={() => downloadFile(proxyCode, 'test-proxy.js')}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    <Download className="w-4 h-4" />
                    Download
                  </button>
                </div>
                <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto text-sm max-h-96">
                  {proxyCode || 'Test proxy will be generated after processing'}
                </pre>
              </div>

              <button
                onClick={downloadAll}
                disabled={!kongYaml}
                className="w-full py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 font-medium"
              >
                Download Complete Migration Package
              </button>
            </div>
          )}

          {activeTab === 'plugins' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Custom Plugins Required</h3>
              {customPlugins.length > 0 ? (
                customPlugins.map((plugin, idx) => (
                  <div key={idx} className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h4 className="font-semibold text-yellow-900">{plugin.name}</h4>
                        <p className="text-sm text-yellow-700 mt-1">Custom plugin implementation required</p>
                      </div>
                      <button
                        onClick={() => downloadFile(generateCustomPluginCode(plugin), `${plugin.name}-handler.lua`)}
                        className="flex items-center gap-2 px-3 py-1 bg-yellow-600 text-white rounded text-sm hover:bg-yellow-700"
                      >
                        <Download className="w-3 h-3" />
                        Download
                      </button>
                    </div>
                    <pre className="mt-3 bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto max-h-48">
                      {generateCustomPluginCode(plugin)}
                    </pre>
                  </div>
                ))
              ) : (
                <p className="text-gray-500">No custom plugins required - all policies map to bundled Kong plugins</p>
              )}
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Migration Log</h3>
              {migrationLog.map((log, idx) => (
                <div
                  key={idx}
                  className={`flex items-start gap-3 p-3 rounded-lg ${
                    log.type === 'error' ? 'bg-red-50 text-red-900' :
                    log.type === 'success' ? 'bg-green-50 text-green-900' :
                    'bg-blue-50 text-blue-900'
                  }`}
                >
                  {log.type === 'error' ? <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" /> :
                   log.type === 'success' ? <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" /> :
                   <FileText className="w-5 h-5 flex-shrink-0 mt-0.5" />}
                  <div className="flex-1">
                    <p className="font-medium">{log.message}</p>
                    <p className="text-xs opacity-70 mt-1">{new Date(log.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="mt-6 bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Start Guide</h3>
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div className="bg-indigo-50 p-4 rounded-lg">
              <h4 className="font-semibold text-indigo-900 mb-2">1. Upload</h4>
              <p className="text-indigo-700">Upload your Apigee shared flow XML file</p>
            </div>
            <div className="bg-green-50 p-4 rounded-lg">
              <h4 className="font-semibold text-green-900 mb-2">2. Review</h4>
              <p className="text-green-700">Check generated Kong config and custom plugins</p>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <h4 className="font-semibold text-purple-900 mb-2">3. Deploy</h4>
              <p className="text-purple-700">Download and deploy using deployment instructions</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApigeeKongMigrator;