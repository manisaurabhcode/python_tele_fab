# Complete Apigee to Kong Migration Workflow

## End-to-End Example: Weather API Migration

This guide walks through a complete migration of a sample Weather API from Apigee to Kong.

## 📦 Sample Apigee Proxy Structure

```
weather-api.zip
├── apiproxy/
│   ├── weather-api.xml              # Proxy definition
│   ├── proxies/
│   │   └── default.xml              # Proxy endpoint
│   ├── targets/
│   │   └── default.xml              # Target endpoint
│   ├── policies/
│   │   ├── VerifyAPIKey.xml         # API Key verification
│   │   ├── Quota-1.xml              # Rate limiting
│   │   ├── CORS.xml                 # CORS policy
│   │   ├── AssignMessage-1.xml      # Request transformation
│   │   └── Javascript-1.xml         # Custom logic
│   └── resources/
│       └── jsc/
│           └── enrichment.js        # JavaScript callout
```

## 🔄 Step-by-Step Migration

### Step 1: Analyze Apigee Configuration

**Upload to Generator:**
```bash
# Using the UI
1. Open the Kong Generator UI
2. Upload weather-api.zip
3. Click "Generate Kong Configuration"

# Using API
curl -X POST http://localhost:5000/api/generate-kong-config \
  -F "file=@weather-api.zip" \
  -o migration-result.json
```

**Expected Output:**
```json
{
  "coverage": {
    "total_policies": 5,
    "migrated_policies": 4,
    "manual_policies": 1,
    "coverage_percentage": 80.0
  },
  "breaking_changes": [
    {
      "category": "Custom Code Migration",
      "description": "Javascript policy 'enrichment' must be rewritten in Lua",
      "impact": "medium",
      "mitigation": "Convert JavaScript logic to Kong Lua plugin"
    }
  ]
}
```

### Step 2: Review Generated Kong Configuration

**Generated kong-config.yaml:**
```yaml
_format_version: "3.0"
_transform: true

# Service Definition
services:
  - name: weather-api
    url: https://api.openweathermap.org/data/2.5
    protocol: https
    port: 443
    path: /
    retries: 5
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000
    tags:
      - apigee-migration
      - weather

# Route Definition
routes:
  - name: weather-api-route
    service: weather-api
    protocols:
      - https
      - http
    paths:
      - /weather
    strip_path: true
    preserve_host: false
    tags:
      - apigee-migration

# Plugins
plugins:
  # API Key Authentication (from VerifyAPIKey)
  - name: key-auth
    service: weather-api
    enabled: true
    tags:
      - apigee-migration
    config:
      key_names:
        - apikey
        - api-key
        - x-api-key
      key_in_header: true
      key_in_query: true
      hide_credentials: true

  # Rate Limiting (from Quota-1)
  - name: rate-limiting
    service: weather-api
    enabled: true
    tags:
      - apigee-migration
    config:
      minute: 100
      hour: null
      policy: local
      fault_tolerant: true
      hide_client_headers: false

  # CORS (from CORS.xml)
  - name: cors
    service: weather-api
    enabled: true
    tags:
      - apigee-migration
    config:
      origins:
        - "*"
      methods:
        - GET
        - POST
        - PUT
        - DELETE
        - OPTIONS
      headers:
        - Accept
        - Authorization
        - Content-Type
        - X-API-Key
      exposed_headers:
        - X-Auth-Token
      credentials: true
      max_age: 3600

  # Request Transformation (from AssignMessage-1)
  - name: request-transformer
    service: weather-api
    enabled: true
    tags:
      - apigee-migration
    config:
      add:
        headers:
          - X-Forwarded-By:Kong
          - X-Service-Name:Weather-API
        querystring: []
      remove:
        headers: []
        querystring: []
      replace:
        headers: []
      rename:
        headers: []

# NOTE: Javascript-1 requires custom Lua plugin
# See custom-enrichment-plugin.lua for implementation
```

### Step 3: Handle Manual Migration (JavaScript Callout)

**Original Apigee JavaScript (enrichment.js):**
```javascript
// Apigee JavaScript Callout
var apiKey = context.getVariable("request.header.apikey");
var location = context.getVariable("request.queryparam.q");

// Enrich request
if (location) {
  context.setVariable("enriched.location", location.toUpperCase());
  context.setVariable("enriched.timestamp", Date.now());
  
  // Add custom header
  context.setVariable("request.header.X-Location", location);
  context.setVariable("request.header.X-Request-Time", new Date().toISOString());
}

// Log
print("Request enriched for location: " + location);
```

**Converted Kong Lua Plugin:**
```lua
-- File: kong/plugins/weather-enrichment/handler.lua
local BasePlugin = require "kong.plugins.base_plugin"

local WeatherEnrichmentHandler = BasePlugin:extend()

WeatherEnrichmentHandler.PRIORITY = 900
WeatherEnrichmentHandler.VERSION = "1.0.0"

function WeatherEnrichmentHandler:new()
  WeatherEnrichmentHandler.super.new(self, "weather-enrichment")
end

function WeatherEnrichmentHandler:access(conf)
  WeatherEnrichmentHandler.super.access(self)
  
  -- Get API key and location
  local apiKey = kong.request.get_header("apikey")
  local location = kong.request.get_query_arg("q")
  
  -- Enrich request
  if location then
    local enriched_location = string.upper(location)
    local timestamp = tostring(ngx.now() * 1000)
    
    -- Add custom headers
    kong.service.request.set_header("X-Location", location)
    kong.service.request.set_header("X-Request-Time", os.date("!%Y-%m-%dT%H:%M:%SZ"))
    kong.service.request.set_header("X-Enriched-Location", enriched_location)
    kong.service.request.set_header("X-Timestamp", timestamp)
    
    -- Log
    kong.log.info("Request enriched for location: ", location)
  end
end

return WeatherEnrichmentHandler
```

**Add to kong-config.yaml:**
```yaml
plugins:
  # ... existing plugins ...
  
  # Custom enrichment plugin
  - name: weather-enrichment
    service: weather-api
    enabled: true
    tags:
      - apigee-migration
      - custom
```

### Step 4: Migrate API Keys

**Export from Apigee:**
```bash
# Using Apigee Management API
curl -H "Authorization: Bearer $APIGEE_TOKEN" \
  "https://api.enterprise.apigee.com/v1/organizations/$ORG/developers" \
  > apigee-developers.json
```

**Import to Kong:**
```bash
# Create consumers and credentials
cat apigee-developers.json | jq -r '.[]' | while read developer; do
  email=$(echo $developer | jq -r '.email')
  apikey=$(echo $developer | jq -r '.credentials[0].consumerKey')
  
  # Create consumer
  curl -X POST http://localhost:8001/consumers \
    --data "username=$email" \
    --data "custom_id=$email"
  
  # Add API key
  curl -X POST http://localhost:8001/consumers/$email/key-auth \
    --data "key=$apikey"
done
```

### Step 5: Deploy to Kong

**Validate Configuration:**
```bash
deck validate -s kong-config.yaml
```

**Expected Output:**
```
✓ Configuration is valid
Services: 1
Routes: 1
Plugins: 5
Consumers: 0
```

**Deploy to Development:**
```bash
# Dry run first
deck diff -s kong-config.yaml --kong-addr http://dev-kong:8001

# Review changes, then sync
deck sync -s kong-config.yaml --kong-addr http://dev-kong:8001
```

**Deployment Output:**
```
creating service weather-api
creating route weather-api-route
creating plugin key-auth (on service weather-api)
creating plugin rate-limiting (on service weather-api)
creating plugin cors (on service weather-api)
creating plugin request-transformer (on service weather-api)
creating plugin weather-enrichment (on service weather-api)

Summary:
  Created: 7
  Updated: 0
  Deleted: 0
```

### Step 6: Test the Migration

**Test 1: API Key Authentication**
```bash
# Without API key (should fail)
curl http://localhost:8000/weather?q=London

# Response:
{
  "message": "No API key found in request"
}

# With valid API key (should succeed)
curl -H "apikey: your-api-key" \
  http://localhost:8000/weather?q=London

# Response:
{
  "coord": {"lon": -0.1257, "lat": 51.5085},
  "weather": [{"main": "Clouds", "description": "broken clouds"}],
  ...
}
```

**Test 2: Rate Limiting**
```bash
# Exceed rate limit
for i in {1..150}; do
  curl -H "apikey: your-api-key" \
    http://localhost:8000/weather?q=London
done

# After 100 requests:
{
  "message": "API rate limit exceeded"
}
```

**Test 3: CORS**
```bash
curl -H "Origin: https://example.com" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     http://localhost:8000/weather

# Response Headers:
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Accept, Authorization, Content-Type, X-API-Key
Access-Control-Max-Age: 3600
```

**Test 4: Request Enrichment**
```bash
curl -v -H "apikey: your-api-key" \
  http://localhost:8000/weather?q=London

# Check request headers sent to upstream:
X-Forwarded-By: Kong
X-Service-Name: Weather-API
X-Location: London
X-Request-Time: 2025-01-15T10:30:00Z
X-Enriched-Location: LONDON
```

### Step 7: Monitor and Validate

**Check Kong Metrics:**
```bash
# Service statistics
curl http://localhost:8001/services/weather-api

# Route statistics  
curl http://localhost:8001/routes/weather-api-route

# Plugin statistics
curl http://localhost:8001/plugins
```

**Enable Prometheus Monitoring:**
```yaml
plugins:
  - name: prometheus
    config:
      per_consumer: true
```

**View Metrics:**
```bash
curl http://localhost:8001/metrics
```

### Step 8: Production Cutover

**Canary Deployment Strategy:**

```yaml
# Create two upstreams: Apigee and Kong
upstreams:
  - name: weather-api-canary
    algorithm: round-robin
    targets:
      - target: apigee-gateway:443
        weight: 90
      - target: kong-gateway:443
        weight: 10

services:
  - name: weather-api
    host: weather-api-canary
```

**Gradually Increase Kong Traffic:**
```bash
# Week 1: 10% Kong, 90% Apigee
# Week 2: 25% Kong, 75% Apigee  
# Week 3: 50% Kong, 50% Apigee
# Week 4: 75% Kong, 25% Apigee
# Week 5: 100% Kong, 0% Apigee

# Update weights via Admin API
curl -X PATCH http://localhost:8001/upstreams/weather-api-canary/targets/kong-target \
  --data "weight=50"
```

## 📊 Migration Report Summary

### Coverage Analysis
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Migration Coverage: 80%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Policies:        5
Auto-Migrated:         4  (80%)
Manual Migration:      1  (20%)
Not Required:          0  (0%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Policy Breakdown

| Apigee Policy | Kong Plugin | Status | Effort |
|---------------|-------------|--------|--------|
| VerifyAPIKey | key-auth | ✅ Auto | Low |
| Quota-1 | rate-limiting | ✅ Auto | Low |
| CORS | cors | ✅ Auto | Low |
| AssignMessage-1 | request-transformer | ✅ Auto | Low |
| Javascript-1 | weather-enrichment | ⚠️ Manual | Medium |

### Breaking Changes
- **JavaScript Callout**: Requires custom Lua plugin (Completed)

### Must-Change Items
- ✅ API Keys migrated
- ✅ Custom Lua plugin developed
- ✅ Configuration tested in dev
- ✅ CORS policies updated

### Timeline
```
Planning:        1 week   ✅ Completed
Development:     2 weeks  ✅ Completed
Testing:         1 week   ✅ Completed
Canary Deploy:   4 weeks  ⏳ In Progress
Full Cutover:    Week 8   📅 Scheduled
```

### Risk Assessment
- **Overall Risk**: LOW
- **Technical Complexity**: Medium
- **Business Impact**: Low (canary deployment)
- **Rollback Time**: < 5 minutes

## ✅ Success Criteria

- [x] 100% API functionality maintained
- [x] Zero downtime migration
- [x] Performance metrics match or exceed Apigee
- [x] All tests passing
- [x] Documentation complete
- [x] Team trained on Kong

## 🎯 Results

### Performance Comparison

| Metric | Apigee | Kong | Improvement |
|--------|--------|------|-------------|
| Avg Latency | 45ms | 38ms | +15% |
| P95 Latency | 120ms | 95ms | +21% |
| Throughput | 1000 req/s | 1200 req/s | +20% |
| Error Rate | 0.01% | 0.005% | +50% |

### Cost Savings
- Infrastructure: 35% reduction
- Licensing: 40% reduction  
- Operational: 25% reduction

## 🎉 Migration Complete!

The Weather API has been successfully migrated from Apigee to Kong with improved performance and reduced costs.

### Next Steps
1. Monitor production traffic for 2 weeks
2. Decommission Apigee infrastructure
3. Document lessons learned
4. Plan next API migration