# Kong Configuration Generator - Complete Documentation

## 🎯 Overview

The Kong Configuration Generator is an enterprise-grade tool that automatically converts Apigee API proxy bundles into Kong Gateway configurations using the decK (Declarative Kong) format. It leverages Claude AI to provide intelligent migration analysis and recommendations.

## 📋 Features

### ✅ Automated Configuration Generation
- Converts Apigee policies to Kong plugins
- Generates decK-compatible YAML configuration
- Maps target endpoints to Kong services
- Creates Kong routes from proxy endpoints

### 📊 Migration Analysis
- **Coverage Percentage**: Shows how much can be auto-migrated
- **Breaking Changes**: Identifies critical issues requiring attention
- **Must-Change Items**: Critical modifications needed
- **Recommended Changes**: Best practices and optimizations

### 🤖 AI-Powered Insights
- Comprehensive migration reports using Claude
- Risk assessment and mitigation strategies
- Testing recommendations
- Timeline estimates

## 🏗️ Architecture

```
┌─────────────────┐
│  React UI       │
│  (Frontend)     │
└────────┬────────┘
         │ HTTP API
         ▼
┌─────────────────┐
│  Flask Backend  │
│  + LangChain    │
└────────┬────────┘
         │
         ├──► Apigee ZIP Parser
         ├──► Policy Mapper
         ├──► Kong Config Generator
         └──► Claude AI (Reports)
```

## 📦 Installation

### Prerequisites
```bash
# System requirements
- Python 3.9+
- Node.js 18+ (for React UI)
- Kong Gateway 3.x
- decK CLI 1.28+
```

### Backend Setup
```bash
# Clone or create project directory
mkdir kong-generator && cd kong-generator

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install flask flask-cors langchain langchain-anthropic anthropic pyyaml

# Set environment variable
export ANTHROPIC_API_KEY=your_api_key_here

# Run the server
python kong_generator.py
```

### Frontend Setup
```bash
# The React component can be used as-is in the artifact viewer
# Or integrate into your React app:
npm install lucide-react
```

## 🔧 API Endpoints

### 1. Generate Kong Configuration
**Endpoint**: `POST /api/generate-kong-config`

**Request**:
```bash
curl -X POST http://localhost:5000/api/generate-kong-config \
  -F "file=@apigee-proxy.zip"
```

**Response**:
```json
{
  "kong_config": {
    "_format_version": "3.0",
    "services": [...],
    "routes": [...],
    "plugins": [...]
  },
  "coverage": {
    "total_policies": 10,
    "migrated_policies": 7,
    "manual_policies": 2,
    "not_required_policies": 1,
    "coverage_percentage": 70.0
  },
  "breaking_changes": [...],
  "migration_report": "..."
}
```

### 2. Export decK Configuration
**Endpoint**: `POST /api/export-deck-config`

**Request**:
```bash
curl -X POST http://localhost:5000/api/export-deck-config \
  -H "Content-Type: application/json" \
  -d '{"kong_config": {...}}' \
  --output kong-config.yaml
```

### 3. Export Migration Report
**Endpoint**: `POST /api/export-migration-report`

**Request**:
```bash
curl -X POST http://localhost:5000/api/export-migration-report \
  -H "Content-Type: application/json" \
  -d '{"migration_report": "..."}' \
  --output migration-report.md
```

## 🔄 Policy Mappings

### Direct Mappings (Auto-Migration)

| Apigee Policy | Kong Plugin | Auto-Migrate | Effort |
|---------------|-------------|--------------|--------|
| VerifyAPIKey | key-auth | ✅ Yes | Low |
| Quota | rate-limiting | ✅ Yes | Low |
| SpikeArrest | rate-limiting | ✅ Yes | Low |
| CORS | cors | ✅ Yes | Low |
| ResponseCache | proxy-cache | ✅ Yes | Low |
| MessageLogging | file-log | ✅ Yes | Low |
| BasicAuthentication | basic-auth | ✅ Yes | Low |
| AssignMessage | request-transformer | ✅ Yes | Medium |

### Manual Migration Required

| Apigee Policy | Kong Solution | Auto-Migrate | Effort |
|---------------|---------------|--------------|--------|
| OAuthV2 | oauth2 plugin | ❌ No | High |
| Javascript | Custom Lua plugin | ❌ No | High |
| JavaCallout | Custom Go/Lua plugin | ❌ No | High |
| ServiceCallout | Custom plugin/upstream | ❌ No | Medium |
| XMLToJSON | Custom Lua plugin | ❌ No | Medium |
| JSONToXML | Custom Lua plugin | ❌ No | Medium |

### Not Required in Kong

- **StatisticsCollector**: Kong has built-in analytics
- **AccessEntity**: Kong uses different entity management
- **KeyValueMapOperations**: Use Kong's native config
- **RaiseFault**: Kong's error handling differs
- **FlowCallout**: Kong uses different flow control

## 📝 Generated Kong Configuration Structure

### Example Output (YAML)
```yaml
_format_version: "3.0"
_transform: true

services:
  - name: weather-api
    url: https://api.openweathermap.org
    protocol: https
    port: 443
    path: /data/2.5
    retries: 5
    connect_timeout: 60000
    write_timeout: 60000
    read_timeout: 60000

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

plugins:
  - name: key-auth
    service: weather-api
    enabled: true
    config:
      key_names:
        - apikey
        - api-key
        - api_key
      key_in_header: true
      key_in_query: true
      hide_credentials: true
  
  - name: rate-limiting
    service: weather-api
    enabled: true
    config:
      minute: 100
      policy: local
      fault_tolerant: true
  
  - name: cors
    service: weather-api
    enabled: true
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
      credentials: true
      max_age: 3600
```

## 🚀 Deployment with decK

### Step 1: Install decK
```bash
# Linux/macOS
curl -sL https://github.com/kong/deck/releases/download/v1.28.2/deck_1.28.2_linux_amd64.tar.gz -o deck.tar.gz
tar -xf deck.tar.gz -C /tmp
sudo cp /tmp/deck /usr/local/bin/

# macOS with Homebrew
brew install deck

# Verify installation
deck version
```

### Step 2: Validate Configuration
```bash
# Validate the generated configuration
deck validate -s kong-config.yaml

# Check for Kong Gateway connectivity
deck ping --kong-addr http://localhost:8001
```

### Step 3: Dry Run (Preview Changes)
```bash
# See what would be changed without applying
deck diff -s kong-config.yaml --kong-addr http://localhost:8001
```

### Step 4: Deploy to Kong
```bash
# Deploy to Kong Gateway
deck sync -s kong-config.yaml --kong-addr http://localhost:8001

# Deploy to Kong with specific workspace
deck sync -s kong-config.yaml --kong-addr http://localhost:8001 --workspace production

# Deploy with selective updates
deck sync -s kong-config.yaml --select-tag migration-v1
```

### Step 5: Verify Deployment
```bash
# List all services
curl http://localhost:8001/services

# List all routes
curl http://localhost:8001/routes

# List all plugins
curl http://localhost:8001/plugins

# Test the API endpoint
curl -H "apikey: your-key" http://localhost:8000/weather?q=London
```

## 📊 Migration Coverage Analysis

### Coverage Calculation
```
Coverage % = (Auto-Migrated Policies / Total Policies) × 100
```

### Example Analysis
```
Total Policies: 15
├── Auto-Migrated: 10 (67%)
├── Manual Migration: 3 (20%)
└── Not Required: 2 (13%)

Coverage: 67%
```

### Coverage Thresholds
- **Excellent** (80-100%): Mostly automated, minimal manual work
- **Good** (60-79%): Some manual work required
- **Fair** (40-59%): Significant manual migration needed
- **Poor** (0-39%): Complex migration, consider redesign

## ⚠️ Breaking Changes

### High Impact Changes

#### 1. Custom Code Migration
**Issue**: JavaScript/Java callouts must be rewritten
```javascript
// Apigee JavaScript
var apiKey = context.getVariable("request.header.apikey");
```

**Solution**: Convert to Kong Lua
```lua
-- Kong Lua plugin
local apiKey = kong.request.get_header("apikey")
```

#### 2. OAuth Configuration
**Issue**: OAuth flows require manual configuration
**Mitigation**: 
- Review OAuth scopes and flows
- Configure Kong OAuth2 plugin
- Test token generation and validation
- Migrate client credentials

#### 3. Data Transformations
**Issue**: Complex XSLT/XML transformations
**Solution**:
- Implement custom Lua plugins
- Use Kong's request/response transformer
- Consider external transformation service

### Medium Impact Changes

#### 1. Service Callouts
**Issue**: ServiceCallout may need custom plugin
**Solution**:
- Evaluate if Kong upstream service is sufficient
- Create custom plugin for complex scenarios
- Use Kong's HTTP client in Lua

#### 2. Conditional Flows
**Issue**: Complex conditional logic
**Solution**:
- Map to Kong route predicates
- Use plugin configurations
- Implement in custom Lua if needed

## 📋 Must-Change Items

### Critical Changes Required Before Deployment

1. **API Keys Migration**
   - Export existing API keys from Apigee
   - Import into Kong using Admin API
   ```bash
   curl -X POST http://localhost:8001/consumers \
     --data "username=customer1"
   
   curl -X POST http://localhost:8001/consumers/customer1/key-auth \
     --data "key=existing-api-key"
   ```

2. **OAuth Credentials**
   - Migrate OAuth2 clients
   - Update client configurations
   - Test token endpoints

3. **Target Endpoints**
   - Update backend service URLs
   - Configure SSL/TLS if needed
   - Verify connectivity

4. **Custom Plugins**
   - Develop and test Lua plugins
   - Deploy to Kong plugin directory
   - Load plugins in Kong configuration

## 🔄 Migration Steps

### Phase 1: Planning (Week 1)
- [x] Analyze Apigee proxy bundles
- [x] Generate Kong configurations
- [x] Review breaking changes
- [ ] Plan custom plugin development
- [ ] Identify dependencies

### Phase 2: Development (Weeks 2-3)
- [ ] Develop custom Lua plugins
- [ ] Configure Kong services and routes
- [ ] Set up testing environment
- [ ] Create test cases

### Phase 3: Testing (Week 4)
- [ ] Unit test custom plugins
- [ ] Integration testing
- [ ] Performance testing
- [ ] Security testing
- [ ] Load testing

### Phase 4: Migration (Week 5)
- [ ] Deploy to staging environment
- [ ] User acceptance testing
- [ ] Fix issues and iterate
- [ ] Prepare rollback plan

### Phase 5: Production (Week 6)
- [ ] Deploy to production
- [ ] Monitor metrics
- [ ] Address any issues
- [ ] Complete migration

## 🧪 Testing Strategy

### 1. Functional Testing
```bash
# Test API key authentication
curl -H "apikey: test-key" http://localhost:8000/api/endpoint

# Test rate limiting
for i in {1..150}; do curl http://localhost:8000/api/endpoint; done

# Test CORS
curl -H "Origin: https://example.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8000/api/endpoint
```

### 2. Performance Testing
```bash
# Use Apache Bench
ab -n 10000 -c 100 http://localhost:8000/api/endpoint

# Use wrk
wrk -t12 -c400 -d30s http://localhost:8000/api/endpoint
```

### 3. Load Testing
```bash
# Use K6
k6 run --vus 1000 --duration 5m load-test.js
```

## 🔒 Security Considerations

### 1. API Key Management
- Rotate keys during migration
- Use secure key generation
- Implement key expiration

### 2. TLS/SSL Configuration
```yaml
services:
  - name: secure-api
    url: https://backend.example.com
    client_certificate: /path/to/cert.pem
    tls_verify: true
```

### 3. Rate Limiting
- Configure appropriate limits
- Set up alerts for threshold breaches
- Implement tiered rate limiting

## 📈 Monitoring and Observability

### Kong Metrics to Monitor
- Request rate and latency
- Error rates (4xx, 5xx)
- Plugin execution time
- Upstream response times
- Cache hit rates

### Integration with Monitoring Tools
```yaml
plugins:
  - name: prometheus
    config:
      per_consumer: true
  
  - name: datadog
    config:
      host: localhost
      port: 8125
      metrics:
        - request_count
        - latency
        - status_count
```

## 🔄 Rollback Plan

### Quick Rollback Steps
1. Keep Apigee running during migration
2. Use traffic splitting/canary deployment
3. Monitor error rates closely
4. Have rollback script ready:

```bash
# Rollback to previous Kong configuration
deck dump -o backup-config.yaml --kong-addr http://localhost:8001
deck sync -s previous-config.yaml --kong-addr http://localhost:8001
```

## 🆘 Troubleshooting

### Common Issues

**Issue**: Plugin not loading
```bash
# Check Kong error logs
tail -f /usr/local/kong/logs/error.log

# Verify plugin is in path
ls -la /usr/local/share/lua/5.1/kong/plugins/
```

**Issue**: Rate limiting not working
```bash
# Check plugin configuration
curl http://localhost:8001/plugins

# Verify plugin is enabled on route
curl http://localhost:8001/routes/{route_id}/plugins
```

**Issue**: Authentication failures
```bash
# List consumers
curl http://localhost:8001/consumers

# Check credentials
curl http://localhost:8001/consumers/{consumer}/key-auth
```

## 📚 Additional Resources

- [Kong Documentation](https://docs.konghq.com/)
- [decK Documentation](https://docs.konghq.com/deck/)
- [Kong Plugin Hub](https://docs.konghq.com/hub/)
- [Lua Plugin Development](https://docs.konghq.com/gateway/latest/plugin-development/)
- [Kong Admin API](https://docs.konghq.com/gateway/latest/admin-api/)

## 🤝 Support

For issues or questions:
1. Review this documentation
2. Check Kong community forums
3. Review generated migration report
4. Test in development environment first

## 📄 License

MIT License - Use freely for your migration projects