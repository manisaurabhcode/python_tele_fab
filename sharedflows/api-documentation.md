# Apigee Shared Flow to Kong Migration - API Documentation

## Overview
This extends your existing Apigee→Kong migration server with dedicated endpoints for Apigee Shared Flow migration, allowing you to migrate shared flows independently or combine them with proxy migrations.

## New Endpoints

### 1. Analyze Shared Flow
**Endpoint:** `POST /api/analyze-shared-flow`

**Purpose:** Analyze one or more Apigee Shared Flow bundles to understand their structure, policies, and migration requirements.

**Request:**
```bash
curl -X POST http://localhost:5000/api/analyze-shared-flow \
  -F "files=@security-shared-flow.zip" \
  -F "files=@logging-shared-flow.zip"
```

**Response:**
```json
{
  "success": true,
  "analysis": {
    "shared_flow_name": "security-flow",
    "shared_flow_type": "reusable_flow",
    "policies": [
      {
        "name": "Verify-API-Key",
        "type": "VerifyAPIKey",
        "config": {...}
      }
    ],
    "flow_structure": {
      "total_flows": 2,
      "total_steps": 5,
      "conditional_steps": 2
    },
    "recommended_approach": "plugin",
    "migration_strategy": "Create a custom Kong plugin for maximum reusability",
    "reusability_score": 75,
    "can_be_kong_plugin": true,
    "complexity": "medium"
  },
  "shared_flow_type": "reusable_flow",
  "can_be_kong_plugin": true
}
```

---

### 2. Generate Shared Flow Migration
**Endpoint:** `POST /api/generate-shared-flow-migration`

**Purpose:** Generate complete Kong configuration from an Apigee Shared Flow, including custom plugins and integration guides.

**Request:**
```bash
curl -X POST http://localhost:5000/api/generate-shared-flow-migration \
  -F "file=@security-shared-flow.zip"
```

**Response:**
```json
{
  "success": true,
  "shared_flow_name": "security-flow",
  "migration_approach": "plugin",
  "kong_config": {
    "_format_version": "3.0",
    "plugins": [...]
  },
  "custom_plugins": {
    "security_flow": "=== FILE: handler.lua ===\n..."
  },
  "integration_guide": "# Integration Guide...",
  "coverage": {
    "total_policies": 5,
    "coverage_percentage": 95
  },
  "validation": {...},
  "migration_report": "# Migration Report...",
  "test_scripts": "#!/bin/bash...",
  "usage_instructions": {
    "as_plugin": "Apply this plugin to any Kong service/route",
    "as_template": "Use this as a template for service configuration",
    "reusability": "This shared flow can be reused across multiple proxies"
  }
}
```

---

### 3. Export Shared Flow Package
**Endpoint:** `POST /api/export-shared-flow-package`

**Purpose:** Export complete migration package as a ZIP file with all resources.

**Request:**
```bash
curl -X POST http://localhost:5000/api/export-shared-flow-package \
  -H "Content-Type: application/json" \
  -d '{
    "shared_flow_name": "security-flow",
    "migration_approach": "plugin",
    "kong_config": {...},
    "custom_plugins": {...},
    "integration_guide": "...",
    "coverage": {...}
  }' \
  --output shared-flow-migration.zip
```

**Response:** ZIP file containing:
```
shared-flow-migration.zip
├── kong-shared-flow-config.yaml
├── custom-plugins/
│   └── security_flow/
│       ├── handler.lua
│       ├── schema.lua
│       └── README.md
├── INTEGRATION_GUIDE.md
├── MIGRATION_REPORT.md
├── USAGE.md
├── test-shared-flow-migration.sh
└── README.md
```

---

### 4. Combine Proxy and Shared Flow
**Endpoint:** `POST /api/combine-proxy-and-shared-flow`

**Purpose:** Migrate a proxy that uses shared flows, combining both into a unified Kong configuration.

**Request:**
```bash
curl -X POST http://localhost:5000/api/combine-proxy-and-shared-flow \
  -F "proxy=@my-api-proxy.zip" \
  -F "shared_flows=@security-flow.zip" \
  -F "shared_flows=@logging-flow.zip"
```

**Response:**
```json
{
  "success": true,
  "proxy_name": "my-api",
  "shared_flows_count": 2,
  "kong_config": {
    "_format_version": "3.0",
    "_comment": "Combined configuration: my-api + 2 shared flow(s)",
    "services": [
      {
        "name": "my-api-service",
        "plugins": [
          // Proxy plugins
          // + Shared flow plugins (security, logging)
        ]
      }
    ]
  },
  "custom_plugins": {...},
  "coverage": {...},
  "validation": {...},
  "integration_notes": "Proxy and shared flows have been combined into a single Kong configuration"
}
```

---

## Integration with Existing Code

### Add to Your Express/Node.js Application

If you're using Node.js, here's how to integrate:

```javascript
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');

// Migrate shared flow
async function migrateSharedFlow(sharedFlowZipPath) {
  const form = new FormData();
  form.append('file', fs.createReadStream(sharedFlowZipPath));
  
  const response = await axios.post(
    'http://localhost:5000/api/generate-shared-flow-migration',
    form,
    { headers: form.getHeaders() }
  );
  
  return response.data;
}

// Combine proxy with shared flows
async function migrateProxyWithSharedFlows(proxyZip, sharedFlowZips) {
  const form = new FormData();
  form.append('proxy', fs.createReadStream(proxyZip));
  
  for (const sfZip of sharedFlowZips) {
    form.append('shared_flows', fs.createReadStream(sfZip));
  }
  
  const response = await axios.post(
    'http://localhost:5000/api/combine-proxy-and-shared-flow',
    form,
    { headers: form.getHeaders() }
  );
  
  return response.data;
}

// Usage
(async () => {
  // Migrate shared flow only
  const sfResult = await migrateSharedFlow('./security-flow.zip');
  console.log('Shared Flow Migration:', sfResult);
  
  // Migrate proxy with shared flows
  const combined = await migrateProxyWithSharedFlows(
    './my-api.zip',
    ['./security-flow.zip', './logging-flow.zip']
  );
  console.log('Combined Migration:', combined);
})();
```

### Add Route to Your Flask App

The endpoints are already included in the code artifact above. Simply add them to your `server.py` and restart:

```python
# Your existing server.py already has these imports and services
# Just copy the new endpoints from the artifact above
```

---

## Installation Steps

### 1. Add Service Files

Create two new files in your `services/` directory:

**services/shared_flow_analyzer.py**
```python
# Copy from the SharedFlowAnalyzer artifact above
```

**services/shared_flow_generator.py**
```python
# Copy from the SharedFlowKongGenerator artifact above
```

### 2. Update server.py

Add the new endpoints from the first artifact to your existing `server.py`.

### 3. Restart Server

```bash
python server.py
```

Server will start on http://localhost:5000 with new endpoints available.

---

## Usage Workflow

### Scenario 1: Migrate Shared Flow Only

```bash
# 1. Analyze shared flow
curl -X POST http://localhost:5000/api/analyze-shared-flow \
  -F "files=@security-flow.zip" | jq '.'

# 2. Generate migration
curl -X POST http://localhost:5000/api/generate-shared-flow-migration \
  -F "file=@security-flow.zip" > shared-flow-result.json

# 3. Export package
curl -X POST http://localhost:5000/api/export-shared-flow-package \
  -H "Content-Type: application/json" \
  -d @shared-flow-result.json \
  --output migration-package.zip
```

### Scenario 2: Migrate Proxy with Shared Flows

```bash
# Combine proxy and shared flows in one call
curl -X POST http://localhost:5000/api/combine-proxy-and-shared-flow \
  -F "proxy=@my-api.zip" \
  -F "shared_flows=@security-flow.zip" \
  -F "shared_flows=@logging-flow.zip" \
  > combined-migration.json
```

### Scenario 3: Automated Migration Pipeline

```python
import requests
import json

def automated_migration_pipeline():
    # 1. Analyze shared flows
    shared_flows = ['security.zip', 'logging.zip', 'transformation.zip']
    analyses = []
    
    for sf in shared_flows:
        with open(sf, 'rb') as f:
            response = requests.post(
                'http://localhost:5000/api/analyze-shared-flow',
                files={'files': f}
            )
            analyses.append(response.json())
    
    # 2. Migrate high-priority shared flows first
    for sf in shared_flows:
        with open(sf, 'rb') as f:
            response = requests.post(
                'http://localhost:5000/api/generate-shared-flow-migration',
                files={'file': f}
            )
            result = response.json()
            
            # 3. Export package
            export_response = requests.post(
                'http://localhost:5000/api/export-shared-flow-package',
                json=result
            )
            
            with open(f'{sf}-migration.zip', 'wb') as out:
                out.write(export_response.content)
    
    # 4. Now migrate proxies with shared flows
    with open('my-api.zip', 'rb') as proxy:
        sf_files = [('shared_flows', open(sf, 'rb')) for sf in shared_flows]
        
        response = requests.post(
            'http://localhost:5000/api/combine-proxy-and-shared-flow',
            files=[('proxy', proxy)] + sf_files
        )
        
        combined = response.json()
        
        # Save combined configuration
        with open('combined-kong-config.yaml', 'w') as f:
            import yaml
            yaml.dump(combined['kong_config'], f)

automated_migration_pipeline()
```

---

## Testing the Endpoints

### Test Script

```bash
#!/bin/bash

# Test shared flow analysis
echo "Testing shared flow analysis..."
curl -X POST http://localhost:5000/api/analyze-shared-flow \
  -F "files=@test-shared-flow.zip" \
  | jq '.analysis.recommended_approach'

# Test shared flow migration
echo "Testing shared flow migration..."
curl -X POST http://localhost:5000/api/generate-shared-flow-migration \
  -F "file=@test-shared-flow.zip" \
  > sf-migration.json

# Check if custom plugins were generated
cat sf-migration.json | jq '.custom_plugins | keys'

# Test combined migration
echo "Testing combined proxy + shared flow migration..."
curl -X POST http://localhost:5000/api/combine-proxy-and-shared-flow \
  -F "proxy=@test-proxy.zip" \
  -F "shared_flows=@test-shared-flow.zip" \
  | jq '.shared_flows_count'

echo "All tests completed!"
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error message here",
  "traceback": "Full Python traceback for debugging"
}
```

Status codes:
- `200` - Success
- `400` - Bad request (missing files, invalid input)
- `500` - Server error (processing failure)

---

## Logging

All endpoints use your existing logging infrastructure:

```python
log.info("Shared Flow Analysis request received")
log.debug("Processing shared flow", extra={"file_count": 3})
log.exception("Shared Flow migration failed")
```

Logs will include correlation IDs from your `X-Request-ID` header.

---

## Performance Considerations

- **Shared flow analysis:** ~2-5 seconds per flow
- **Migration generation:** ~5-15 seconds (includes LLM calls)
- **Combined migration:** ~10-30 seconds (proxy + multiple shared flows)

For large batches, consider:
1. Processing shared flows in parallel
2. Caching shared flow analyses
3. Using background task queue (Celery)

---

## Next Steps

1. Copy service files to `services/` directory
2. Add new endpoints to `server.py`
3. Restart your Flask server
4. Test with sample shared flows
5. Integrate into your automation pipeline

The endpoints seamlessly integrate with your existing authentication, logging, and LLM configuration systems!
