# Apigee to Kong Migration Analyzer - Complete Setup Guide

## 🎯 Overview

This tool analyzes Apigee API proxy bundles and shared flows to determine Kong migration complexity using AI-powered analysis with Claude (Sonnet 4).

## 📋 Prerequisites

- Python 3.9+
- Node.js 18+ (for React frontend)
- Anthropic API Key
- Apigee proxy bundle ZIP files

## 🚀 Installation

### Backend Setup

```bash
# Create project directory
mkdir apigee-kong-analyzer
cd apigee-kong-analyzer

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
ANTHROPIC_API_KEY=your_anthropic_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True
EOF
```

### Frontend Setup (Optional - for standalone UI)

```bash
# Create React app
npx create-react-app frontend
cd frontend

# Install dependencies
npm install lucide-react

# Copy the React component to src/App.js
```

## 📁 Project Structure

```
apigee-kong-analyzer/
├── backend/
│   ├── app.py                    # Flask API server
│   ├── analyzer.py               # Core analyzer with LangChain
│   ├── config.py                 # Configuration management
│   ├── advanced_analyzer.py      # Enhanced pattern detection
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   └── App.js               # React UI component
│   └── package.json
├── config/
│   └── custom_rules.json        # Customizable scoring rules
├── .env                          # Environment variables
└── README.md
```

## 🔧 Configuration

### Customize Complexity Scoring Rules

Create `custom_rules.json`:

```json
{
  "policies": {
    "custom_policy": 5,
    "javascript_callout": 10,
    "java_callout": 15,
    "service_callout": 8
  },
  "thresholds": {
    "simple": {"min": 0, "max": 30},
    "medium": {"min": 31, "max": 70},
    "complex": {"min": 71, "max": 999}
  }
}
```

### Load Custom Rules in Code

```python
from config import MigrationConfig

# Load custom configuration
config = MigrationConfig('config/custom_rules.json')

# Initialize analyzer with custom rules
from dataclasses import asdict
rules = ComplexityRule(**config.rules['policies'])
analyzer = ApigeeProxyAnalyzer(rules=rules)
```

## 🎮 Usage

### Method 1: React UI with Claude API (Client-Side)

The React artifact above includes direct Claude API integration. Simply:

1. Open the artifact
2. Upload your Apigee proxy ZIP files
3. Click "Analyze Migration Complexity"
4. View detailed results

**Note**: This uses client-side API calls to Claude directly from the browser.

### Method 2: Python Backend API

```bash
# Start Flask server
python app.py
```

Then use curl or Postman:

```bash
curl -X POST http://localhost:5000/api/analyze \
  -F "files=@proxy1.zip" \
  -F "files=@proxy2.zip"
```

### Method 3: Direct Python Script

```python
from analyzer import ApigeeProxyAnalyzer

# Initialize
analyzer = ApigeeProxyAnalyzer(api_key='your_api_key')

# Analyze proxies
result = analyzer.analyze_proxies(['proxy1.zip', 'shared_flow1.zip'])

# Generate report
report = analyzer.generate_migration_report(result, 'migration_report.md')
print(report)
```

## 🔍 Understanding the Analysis

### Complexity Levels

| Level | Score Range | Description |
|-------|-------------|-------------|
| **Simple** | 0-30 | Basic policies, straightforward migration |
| **Medium** | 31-70 | Some custom logic, moderate effort |
| **Complex** | 71+ | Heavy customization, significant effort |

### Policy Scoring

| Policy Type | Points | Kong Equivalent | Effort |
|-------------|--------|-----------------|--------|
| VerifyAPIKey | 2 | key-auth | Low |
| Quota/SpikeArrest | 3 | rate-limiting | Low |
| AssignMessage | 2 | request/response-transformer | Medium |
| JavaScript | 10 | Custom Lua plugin | High |
| JavaCallout | 15 | Custom Go/Lua plugin | High |
| ServiceCallout | 8 | Custom logic + upstream | Medium |
| OAuth | 10 | oauth2 plugin | Medium |

### Features Not Required in Kong

These Apigee features are handled differently or natively in Kong:

- **StatisticsCollector**: Kong has built-in analytics
- **AccessEntity**: Kong uses different entity management
- **KeyValueMapOperations**: Use Kong's native configuration
- **RaiseFault**: Kong has different error handling
- **FlowCallout**: Kong uses different flow control

## 🧪 Testing

### Test with Sample Proxy

```python
# test_analyzer.py
import unittest
from analyzer import ApigeeProxyAnalyzer

class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = ApigeeProxyAnalyzer()
    
    def test_simple_proxy(self):
        result = self.analyzer.analyze_proxies(['samples/simple_proxy.zip'])
        self.assertEqual(result.complexity, 'simple')
        self.assertLessEqual(result.totalScore, 30)
    
    def test_complex_proxy(self):
        result = self.analyzer.analyze_proxies(['samples/complex_proxy.zip'])
        self.assertGreater(result.totalScore, 70)

if __name__ == '__main__':
    unittest.main()
```

## 🎨 Customization Options

### 1. Adjust Policy Weights

```python
rules = ComplexityRule(
    javascript_callout=15,  # Increase from 10
    java_callout=20,        # Increase from 15
    service_callout=10      # Increase from 8
)
analyzer = ApigeeProxyAnalyzer(rules=rules)
```

### 2. Modify Thresholds

```python
config = MigrationConfig()
config.rules['thresholds']['simple']['max'] = 40  # Increase simple threshold
config.rules['thresholds']['medium']['max'] = 80
config.save_config('custom_rules.json')
```

### 3. Add Custom Kong Mappings

```python
config.rules['kong_equivalents']['CustomPolicy'] = {
    'plugin': 'your-custom-plugin',
    'effort': 'high',
    'notes': 'Requires custom development'
}
```

## 📊 Output Examples

### JSON Response

```json
{
  "complexity": "medium",
  "totalScore": 45,
  "breakdown": [
    {"category": "JavaScript Callout", "count": 2, "points": 20},
    {"category": "ServiceCallout", "count": 1, "points": 8},
    {"category": "Quota Policies", "count": 3, "points": 9}
  ],
  "migrationNotes": [
    "JavaScript callouts need to be rewritten in Lua",
    "Consider using Kong's rate-limiting plugin for quota management"
  ],
  "notRequiredForMigration": [
    "StatisticsCollector - Kong has built-in analytics"
  ],
  "kongEquivalents": [
    {
      "apigeePolicy": "VerifyAPIKey",
      "kongPlugin": "key-auth",
      "effort": "low"
    }
  ],
  "estimatedEffort": "5-7 days"
}
```

### Markdown Report

The tool generates a comprehensive markdown report with:
- Overall complexity assessment
- Detailed score breakdown
- Migration notes and considerations
- Kong plugin mappings
- Effort estimates

## 🔐 Security Best Practices

1. **API Key Management**: Store API keys in environment variables, never in code
2. **File Upload Validation**: The backend validates file types and sizes
3. **Rate Limiting**: Consider implementing rate limits for the API endpoint
4. **CORS Configuration**: Configure CORS appropriately for production

## 🐛 Troubleshooting

### Common Issues

**Issue**: "API key not found"
```bash
# Solution: Set environment variable
export ANTHROPIC_API_KEY=your_key_here
```

**Issue**: "Module not found"
```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Issue**: "Cannot parse ZIP file"
```bash
# Solution: Ensure ZIP file is valid Apigee proxy bundle
unzip -t proxy.zip
```

## 🚢 Deployment

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

### Environment Variables for Production

```bash
ANTHROPIC_API_KEY=sk-ant-xxx
FLASK_ENV=production
ALLOWED_ORIGINS=https://yourdomain.com
MAX_FILE_SIZE=10485760
```

## 📈 Roadmap

- [ ] Support for direct Apigee API integration
- [ ] Batch processing for multiple organizations
- [ ] Kong configuration generator
- [ ] Migration plan timeline generator
- [ ] Cost estimation calculator
- [ ] PDF report generation

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Additional policy pattern detection
- More Kong plugin mappings
- Enhanced complexity algorithms
- UI/UX improvements

## 📄 License

MIT License - feel free to use and modify for your migration projects.

## 📞 Support

For issues or questions:
- Check the troubleshooting section
- Review sample proxy bundles
- Test with simplified configurations first

## 🎓 Resources

- [Kong Documentation](https://docs.konghq.com/)
- [Apigee Documentation](https://cloud.google.com/apigee/docs)
- [LangChain Documentation](https://python.langchain.com/)
- [Claude API Documentation](https://docs.anthropic.com/)