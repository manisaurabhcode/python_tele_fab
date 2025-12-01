# Real-World Migration Examples

## Example 1: E-Commerce API Gateway

### Input: Apigee Proxy Bundle

**Proxy Structure:**
```
ecommerce-api/
├── VerifyAPIKey.xml
├── Quota-Bronze.xml (100 req/min)
├── Quota-Silver.xml (500 req/min)
├── Quota-Gold.xml (2000 req/min)
├── CORS.xml
├── AssignMessage-AddHeaders.xml
├── AssignMessage-RemoveInternalHeaders.xml
├── ResponseCache.xml
├── MessageLogging.xml
└── JavaScript-PriceCalculator.js
```

### AI Analysis Output

```json
{
  "bundling_opportunities": [
    {
      "bundle_name": "authentication-with-tiered-rate-limiting",
      "policies": ["VerifyAPIKey", "Quota-Bronze", "Quota-Silver", "Quota-Gold"],
      "reason": "Can use Kong's consumer tiers with rate-limiting",
      "single_plugin": "key-auth + rate-limiting (consumer-scoped)"
    },
    {
      "bundle_name": "request-manipulation",
      "policies": ["AssignMessage-AddHeaders", "AssignMessage-RemoveInternalHeaders"],
      "reason": "Both are header transformations",
      "single_plugin": "request-transformer"
    }
  ]
}
```

### Generated Kong Configuration

```yaml
_format_version: "3.0"

services:
  - name: ecommerce-api
    url: https://backend.ecommerce.com/api
    tags: [ecommerce, production]

routes:
  - name: ecommerce-products
    service: ecommerce-api
    paths: [/products]
    strip_path: true

# Consumer Tiers (AI-suggested approach)
consumers:
  - username: bronze-tier
    tags: [bronze]
  - username: silver-tier
    tags: [silver]
  - username: gold-tier
    tags: [gold]

plugins:
  # Bundled: VerifyAPIKey + Tiered Quotas
  - name: key-auth
    service: ecommerce-api
    config:
      key_names: [apikey, x-api-key]
      hide_credentials: true
  
  # Bronze tier rate limit
  - name: rate-limiting
    consumer: bronze-tier
    config:
      minute: 100
      policy: local
      tags: [bronze-tier]
  
  # Silver tier rate limit
  - name: rate-limiting
    consumer: silver-tier
    config:
      minute: 500
      policy: local
      tags: [silver-tier]
  
  # Gold tier rate limit
  - name: rate-limiting
    consumer: gold-tier
    config:
      minute: 2000
      policy: local
      tags: [gold-tier]
  
  # CORS
  - name: cors
    service: ecommerce-api
    config:
      origins: ["https://shop.ecommerce.com"]
      credentials: true
  
  # Bundled: Multiple AssignMessage policies
  - name: request-transformer
    service: ecommerce-api
    config:
      add:
        headers:
          - X-Service-Name:ecommerce-api
          - X-Environment:production
          - X-Request-Time:$(date)
      remove:
        headers:
          - X-Internal-Token
          - X-Backend-Secret
  
  # Response Cache
  - name: proxy-cache
    service: ecommerce-api
    config:
      strategy: memory
      cache_ttl: 300
      content_type: [application/json]
  
  # Logging
  - name: file-log
    service: ecommerce-api
    config:
      path: /var/log/kong/ecommerce.log
  
  # Custom Plugin: PriceCalculator (AI-converted from JavaScript)
  - name: price-calculator
    service: ecommerce-api
    config:
      currency: USD
      discount_enabled: true
```

### AI-Generated Custom Plugin: PriceCalculator

**Original JavaScript:**
```javascript
// Apigee JavaScript: PriceCalculator.js
var basePrice = context.getVariable("response.content.price");
var discount = context.getVariable("request.header.discount-code");
var userTier = context.getVariable("request.header.user-tier");

var finalPrice = basePrice;

// Apply tier-based discount
if (userTier === "gold") {
    finalPrice = basePrice * 0.9; // 10% off
} else if (userTier === "silver") {
    finalPrice = basePrice * 0.95; // 5% off
}

// Apply discount code
if (discount === "SAVE20") {
    finalPrice = finalPrice * 0.8;
}

context.setVariable("response.content.final_price", finalPrice);
context.setVariable("response.content.savings", basePrice - finalPrice);
```

**AI-Generated Lua Plugin:**
```lua
-- handler.lua (AI-generated)
local PriceCalculatorHandler = {
  PRIORITY = 800,
  VERSION = "1.0.0"
}

function PriceCalculatorHandler:body_filter(conf)
  local body = kong.response.get_raw_body()
  if not body then return end
  
  local cjson = require "cjson"
  local ok, json_body = pcall(cjson.decode, body)
  if not ok then return end
  
  local base_price = json_body.price
  if not base_price then return end
  
  local discount_code = kong.request.get_header("discount-code")
  local user_tier = kong.request.get_header("user-tier")
  
  local final_price = base_price
  
  -- Apply tier discount
  if user_tier == "gold" then
    final_price = final_price * 0.9
  elseif user_tier == "silver" then
    final_price = final_price * 0.95
  end
  
  -- Apply discount code
  if discount_code == "SAVE20" then
    final_price = final_price * 0.8
  end
  
  json_body.final_price = final_price
  json_body.savings = base_price - final_price
  json_body.discount_applied = user_tier or discount_code
  
  kong.response.set_raw_body(cjson.encode(json_body))
end

return PriceCalculatorHandler
```

### Coverage Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
E-Commerce API Migration Coverage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total Policies: 9
Auto-Migrated: 8 (89%)
Bundled: 5 policies → 2 plugins (60% efficiency)
Custom Plugins: 1 (AI-generated Lua)

Coverage: 89%
Bundling Efficiency: 60%

Policy Breakdown:
✓ VerifyAPIKey → key-auth
✓ Quota (3 tiers) → rate-limiting (consumer-scoped)
✓ CORS → cors
✓ AssignMessage (2x) → request-transformer (bundled)
✓ ResponseCache → proxy-cache
✓ MessageLogging → file-log
⚠ JavaScript-PriceCalculator → custom Lua plugin (auto-generated)

Estimated Migration Time: 4-6 hours
Manual Work Required: Plugin installation, consumer setup
```

### Manual Steps

**Step 1: Create Consumer Tiers (Critical)**
```bash
# Create consumers for each tier
curl -X POST http://localhost:8001/consumers \
  --data "username=bronze-tier" \
  --data "tags=bronze"

curl -X POST http://localhost:8001/consumers \
  --data "username=silver-tier" \
  --data "tags=silver"

curl -X POST http://localhost:8001/consumers \
  --data "username=gold-tier" \
  --data "tags=gold"

# Assign API keys to tiers
# Bronze customers
cat bronze_customers.txt | while read customer_key; do
  curl -X POST http://localhost:8001/consumers/bronze-tier/key-auth \
    --data "key=$customer_key"
done

# Repeat for silver and gold
```

**Step 2: Install Custom Plugin (High Priority)**
```bash
# Copy plugin files
sudo mkdir -p /usr/local/share/lua/5.1/kong/plugins/price-calculator
sudo cp handler.lua /usr/local/share/lua/5.1/kong/plugins/price-calculator/
sudo cp schema.lua /usr/local/share/lua/5.1/kong/plugins/price-calculator/

# Enable in kong.conf
echo "plugins = bundled,price-calculator" | sudo tee -a /etc/kong/kong.conf

# Restart Kong
sudo kong restart
```

---

## Example 2: Financial Services API

### Input: Complex Banking API

**Proxy Structure:**
```
banking-api/
├── OAuthV2-Validate.xml
├── VerifyJWT.xml
├── LDAPAuthentication.xml
├── ServiceCallout-FraudCheck.xml
├── JavaScript-TransactionValidator.js
├── JSONThreatProtection.xml
├── XMLThreatProtection.xml
├── AssignMessage-Audit.xml
└── MessageLogging-Compliance.xml
```

### AI Bundling Analysis

```
Complex Security Flow Detected

Bundling Strategy:
1. OAuthV2 + VerifyJWT → Single authentication flow
   Reason: JWT validation is part of OAuth flow
   
2. ServiceCallout-FraudCheck + JavaScript-TransactionValidator 
   → Single custom plugin
   Reason: Both validate transaction, can combine logic

3. JSON + XML ThreatProtection → Request validation plugin
   Reason: Both are input validation, single execution point

Result: 9 policies → 5 Kong plugins (44% reduction)
```

### Generated Kong Configuration

```yaml
_format_version: "3.0"

services:
  - name: banking-api
    url: https://core-banking.example.com
    client_certificate:
      id: banking-mtls-cert
    retries: 3
    connect_timeout: 30000

routes:
  - name: banking-transactions
    service: banking-api
    paths: [/api/v1/transactions]
    methods: [POST, GET]
    protocols: [https]

plugins:
  # OAuth2 + JWT bundled flow
  - name: openid-connect
    service: banking-api
    config:
      issuer: https://auth.example.com
      client_id: banking-api-client
      client_secret: ${OAUTH_CLIENT_SECRET}
      scopes: [openid, transactions, read_balance]
      bearer_only: true
      verify_signature: true
      jwt_session_cookie: false
  
  # Rate limiting (conservative for financial services)
  - name: rate-limiting
    service: banking-api
    config:
      minute: 60
      policy: redis
      redis_host: redis.example.com
      fault_tolerant: false  # Fail closed for security
  
  # Custom: Fraud Check + Transaction Validation (bundled)
  - name: fraud-and-validation
    service: banking-api
    config:
      fraud_check_url: https://fraud-api.example.com/check
      max_transaction_amount: 10000
      require_2fa_above: 5000
      blocked_countries: [XX, YY]
  
  # Request Validation (JSON + XML bundled)
  - name: request-validator
    service: banking-api
    config:
      body_schema: |
        {
          "type": "object",
          "required": ["amount", "account_from", "account_to"],
          "properties": {
            "amount": {"type": "number", "minimum": 0.01},
            "account_from": {"type": "string", "pattern": "^[0-9]{10}$"},
            "account_to": {"type": "string", "pattern": "^[0-9]{10}$"}
          }
        }
  
  # Compliance Logging
  - name: http-log
    service: banking-api
    config:
      http_endpoint: https://compliance-log.example.com/ingest
      method: POST
      content_type: application/json
      timeout: 10000
      keepalive: 60000
```

### AI-Generated Custom Plugin: Fraud & Validation

```lua
-- fraud-and-validation/handler.lua (AI-generated)
local http = require "resty.http"
local cjson = require "cjson"

local FraudAndValidationHandler = {
  PRIORITY = 950,
  VERSION = "1.0.0"
}

function FraudAndValidationHandler:access(conf)
  -- Get transaction details
  local body = kong.request.get_raw_body()
  local transaction = cjson.decode(body)
  
  -- Validation: Check amount
  if transaction.amount > conf.max_transaction_amount then
    return kong.response.exit(400, {
      error = "Transaction amount exceeds limit",
      max_allowed = conf.max_transaction_amount
    })
  end
  
  -- Validation: Require 2FA for large transactions
  if transaction.amount > conf.require_2fa_above then
    local two_fa_token = kong.request.get_header("X-2FA-Token")
    if not two_fa_token then
      return kong.response.exit(401, {
        error = "2FA required for transactions above " .. conf.require_2fa_above,
        requires_2fa = true
      })
    end
  end
  
  -- Fraud Check: External service callout
  local httpc = http.new()
  httpc:set_timeout(conf.timeout or 5000)
  
  local fraud_check_body = {
    transaction_id = transaction.transaction_id,
    amount = transaction.amount,
    account_from = transaction.account_from,
    account_to = transaction.account_to,
    ip_address = kong.client.get_forwarded_ip(),
    user_agent = kong.request.get_header("User-Agent")
  }
  
  local res, err = httpc:request_uri(conf.fraud_check_url, {
    method = "POST",
    body = cjson.encode(fraud_check_body),
    headers = {
      ["Content-Type"] = "application/json",
      ["Authorization"] = "Bearer " .. conf.fraud_api_token
    }
  })
  
  if not res then
    kong.log.err("Fraud check failed: ", err)
    return kong.response.exit(503, {
      error = "Fraud check service unavailable"
    })
  end
  
  local fraud_result = cjson.decode(res.body)
  
  if fraud_result.risk_score > 0.7 then
    kong.log.warn("High risk transaction blocked: ", transaction.transaction_id)
    return kong.response.exit(403, {
      error = "Transaction blocked due to fraud risk",
      risk_score = fraud_result.risk_score,
      contact_support = true
    })
  end
  
  -- Add fraud score to request for audit
  kong.service.request.set_header("X-Fraud-Score", tostring(fraud_result.risk_score))
  kong.service.request.set_header("X-Fraud-Check-Id", fraud_result.check_id)
end

return FraudAndValidationHandler
```

### Migration Report Highlights

```markdown
# Banking API Migration Report

## Security Considerations

⚠️ **CRITICAL**: Financial services API requires additional review:

1. **OAuth2 Migration**
   - Apigee OAuthV2 → Kong OpenID Connect
   - MUST verify token validation logic
   - MUST test all OAuth flows (authorization code, client credentials)
   - MUST configure proper token expiration

2. **Fraud Check Integration**
   - External service callout bundled with validation
   - Timeout set to 5s (configurable)
   - Fail-closed strategy recommended
   - Consider circuit breaker pattern

3. **Compliance Logging**
   - All transactions logged to compliance endpoint
   - PII data handling MUST be reviewed
   - Retention policy MUST be configured
   - Encryption in transit enforced

## Breaking Changes

HIGH IMPACT:
- OAuth flow changes: Clients may need to update token endpoint
- 2FA enforcement: New header required for large transactions
- Rate limiting: More restrictive (60/min vs 100/min in Apigee)

## Testing Requirements

CRITICAL TESTS:
1. OAuth token validation with expired tokens
2. Transaction validation with invalid amounts
3. Fraud check timeout handling
4. 2FA flow for large transactions
5. Compliance logging verification
6. Rate limit enforcement
7. Certificate validation (mTLS)

## Timeline

- Plugin Development: 2 days
- Security Review: 3 days
- Testing: 5 days
- Staging Deployment: 1 day
- Production Canary: 1 week
- Full Cutover: After approval

Total: ~3 weeks
```

---

## Example 3: Multi-Region API Gateway

### Scenario: Global E-Learning Platform

**Requirements:**
- 5 Apigee proxies (per region)
- Geolocation-based routing
- Content caching per region
- Quota varies by region

### AI Recommendation

```
Multi-Region Optimization Detected

Recommendation: Use Kong's workspace feature for region isolation

Architecture:
┌─────────────────────────────────────────────────┐
│ Kong Gateway (Global Control Plane)             │
├─────────────────────────────────────────────────┤
│ Workspace: US-East                              │
│ Workspace: EU-West                              │
│ Workspace: APAC                                 │
└─────────────────────────────────────────────────┘

Benefits:
- Single Kong instance, multiple isolated configs
- Region-specific policies
- Centralized management
- Reduced infrastructure costs (vs 5 separate Kong instances)

Bundling Across Regions:
- Common authentication: Shared key-auth plugin
- Region-specific: Different rate limits, caching TTLs
- Global: CORS, logging policies
```

### Generated Multi-Workspace Configuration

```yaml
# Global configuration
_format_version: "3.0"
_workspace: default

# Global plugins (applied to all workspaces)
plugins:
  - name: prometheus
    config:
      per_consumer: true
  
  - name: cors
    config:
      origins: ["*"]
      credentials: true

---
# US-East Workspace
_format_version: "3.0"
_workspace: us-east

services:
  - name: elearning-api-us
    url: https://us-backend.elearning.com

plugins:
  - name: rate-limiting
    service: elearning-api-us
    config:
      minute: 100  # Higher limit for US region

---
# EU-West Workspace
_format_version: "3.0"
_workspace: eu-west

services:
  - name: elearning-api-eu
    url: https://eu-backend.elearning.com

plugins:
  - name: rate-limiting
    service: elearning-api-eu
    config:
      minute: 80  # GDPR-compliant conservative limit
  
  - name: request-transformer
    service: elearning-api-eu
    config:
      add:
        headers:
          - X-GDPR-Compliant:true
          - X-Data-Region:EU
```

---

## Key Takeaways from Examples

### 1. **Bundling Saves Resources**
- E-Commerce: 9 policies → 7 plugins (22% reduction)
- Banking: 9 policies → 5 plugins (44% reduction)  
- Average: 30-40% fewer plugins

### 2. **Custom Plugins Are Powerful**
- AI converts JavaScript/Java to idiomatic Lua
- Maintains business logic exactly
- Often combines multiple policies into one

### 3. **Security Gets Special Attention**
- Financial services receive stricter validation
- Compliance logging automatically included
- Fail-closed strategies recommended

### 4. **Migration Complexity Varies**
- Simple APIs: 80-90% coverage
- Complex APIs: 60-70% coverage
- Custom code: Always requires review

### 5. **Regional Differences Matter**
- Multi-region deployments use workspaces
- Different rate limits per region
- Compliance requirements (GDPR, etc.) considered