# requirements.txt
langchain==0.1.0
langchain-anthropic==0.1.0
anthropic==0.18.1
pydantic==2.5.0
flask==3.0.0
flask-cors==4.0.0
python-dotenv==1.0.0

# ============================================
# .env.example
# ============================================
ANTHROPIC_API_KEY=your_api_key_here
FLASK_ENV=development
FLASK_DEBUG=True

# ============================================
# config.py - Configuration Management
# ============================================
"""
Configuration file for customizable complexity rules
"""

import json
from typing import Dict, Any


class MigrationConfig:
    """Manages configurable complexity rules and thresholds"""
    
    DEFAULT_RULES = {
        "policies": {
            "custom_policy": 5,
            "javascript_callout": 10,
            "python_callout": 10,
            "service_callout": 8,
            "java_callout": 15,
            "oauth_jwt_complex": 10,
            "transformation_policy": 8,
            "message_logging": 5,
            "quota_spike_arrest": 3,
            "assign_message": 2,
            "verify_api_key": 2,
            "cors_policy": 1,
            "cache_policy": 4,
            "extract_variables_regex": 6,
            "conditional_flows_complex": 7,
            "shared_flow_reference": 3,
            "multiple_target_servers": 5,
            "custom_analytics": 6
        },
        "thresholds": {
            "simple": {"min": 0, "max": 30},
            "medium": {"min": 31, "max": 70},
            "complex": {"min": 71, "max": 999}
        },
        "kong_equivalents": {
            "VerifyAPIKey": {
                "plugin": "key-auth",
                "effort": "low",
                "notes": "Direct mapping available"
            },
            "Quota": {
                "plugin": "rate-limiting",
                "effort": "low",
                "notes": "Kong's rate-limiting plugin provides similar functionality"
            },
            "SpikeArrest": {
                "plugin": "rate-limiting",
                "effort": "low",
                "notes": "Use rate-limiting with appropriate configuration"
            },
            "OAuthV2": {
                "plugin": "oauth2",
                "effort": "medium",
                "notes": "May require additional configuration"
            },
            "CORS": {
                "plugin": "cors",
                "effort": "low",
                "notes": "Direct equivalent available"
            },
            "AssignMessage": {
                "plugin": "request-transformer / response-transformer",
                "effort": "medium",
                "notes": "Headers and body transformations"
            },
            "JavaCallout": {
                "plugin": "Custom Plugin (Lua/Go)",
                "effort": "high",
                "notes": "Requires rewriting in Lua or Go"
            },
            "JavaScript": {
                "plugin": "Custom Plugin (Lua)",
                "effort": "high",
                "notes": "Logic must be translated to Lua"
            },
            "ServiceCallout": {
                "plugin": "request-termination + upstream",
                "effort": "medium",
                "notes": "May need custom plugin for complex scenarios"
            },
            "ResponseCache": {
                "plugin": "proxy-cache",
                "effort": "low",
                "notes": "Kong has built-in caching"
            },
            "MessageLogging": {
                "plugin": "file-log / http-log",
                "effort": "low",
                "notes": "Multiple logging options available"
            },
            "JSONThreatProtection": {
                "plugin": "Custom validation",
                "effort": "medium",
                "notes": "May need custom Lua plugin"
            },
            "XMLThreatProtection": {
                "plugin": "Custom validation",
                "effort": "medium",
                "notes": "May need custom Lua plugin"
            }
        },
        "not_required": [
            "StatisticsCollector - Kong has built-in analytics",
            "AccessEntity - Kong handles entity lookups differently",
            "KeyValueMapOperations - Use Kong's native configuration",
            "RaiseFault - Kong's error handling is different",
            "FlowCallout - Kong uses different flow control"
        ]
    }
    
    def __init__(self, config_file: str = None):
        """Load configuration from file or use defaults"""
        if config_file:
            self.rules = self.load_config(config_file)
        else:
            self.rules = self.DEFAULT_RULES.copy()
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Config file {config_file} not found. Using defaults.")
            return self.DEFAULT_RULES.copy()
    
    def save_config(self, config_file: str):
        """Save current configuration to file"""
        with open(config_file, 'w') as f:
            json.dump(self.rules, f, indent=2)
    
    def update_policy_score(self, policy_name: str, score: int):
        """Update score for a specific policy"""
        if policy_name in self.rules['policies']:
            self.rules['policies'][policy_name] = score
    
    def get_complexity_level(self, score: int) -> str:
        """Determine complexity level based on score"""
        for level, threshold in self.rules['thresholds'].items():
            if threshold['min'] <= score <= threshold['max']:
                return level
        return 'complex'


# ============================================
# advanced_analyzer.py - Enhanced Analyzer
# ============================================
"""
Enhanced analyzer with additional features
"""

from typing import List, Dict
import re


class EnhancedApigeeAnalyzer:
    """Enhanced analyzer with pattern detection"""
    
    POLICY_PATTERNS = {
        'AssignMessage': r'<AssignMessage.*?>',
        'VerifyAPIKey': r'<VerifyAPIKey.*?>',
        'Quota': r'<Quota.*?>',
        'SpikeArrest': r'<SpikeArrest.*?>',
        'OAuthV2': r'<OAuthV2.*?>',
        'ServiceCallout': r'<ServiceCallout.*?>',
        'JavaScript': r'<Javascript.*?>',
        'JavaCallout': r'<JavaCallout.*?>',
        'JSONToXML': r'<JSONToXML.*?>',
        'XMLToJSON': r'<XMLToJSON.*?>',
        'ExtractVariables': r'<ExtractVariables.*?>',
        'ResponseCache': r'<ResponseCache.*?>',
        'MessageLogging': r'<MessageLogging.*?>',
        'CORS': r'<CORS.*?>'
    }
    
    def detect_policies(self, xml_content: str) -> Dict[str, int]:
        """Detect and count Apigee policies in XML"""
        policy_counts = {}
        
        for policy_name, pattern in self.POLICY_PATTERNS.items():
            matches = re.findall(pattern, xml_content, re.IGNORECASE)
            if matches:
                policy_counts[policy_name] = len(matches)
        
        return policy_counts
    
    def detect_shared_flows(self, xml_content: str) -> List[str]:
        """Detect shared flow references"""
        pattern = r'<FlowCallout.*?name=["\']([^"\']+)["\']'
        return re.findall(pattern, xml_content)
    
    def detect_conditional_complexity(self, xml_content: str) -> int:
        """Analyze conditional flow complexity"""
        condition_pattern = r'<Condition>(.*?)</Condition>'
        conditions = re.findall(condition_pattern, xml_content, re.DOTALL)
        
        complexity = 0
        for condition in conditions:
            # Count operators and variables
            operators = len(re.findall(r'(and|or|not|\&\&|\|\|)', condition, re.IGNORECASE))
            complexity += operators
        
        return complexity
    
    def analyze_javascript_complexity(self, js_content: str) -> Dict[str, Any]:
        """Analyze JavaScript callout complexity"""
        return {
            'lines': len(js_content.split('\n')),
            'has_async': 'async' in js_content or 'await' in js_content,
            'has_http_calls': 'httpClient' in js_content or 'fetch' in js_content,
            'has_crypto': 'crypto' in js_content,
            'complexity_estimate': 'high' if len(js_content) > 500 else 'medium'
        }


# ============================================
# Usage Example
# ============================================
if __name__ == "__main__":
    # Load custom configuration
    config = MigrationConfig()
    
    # Customize a policy score
    config.update_policy_score('java_callout', 20)
    
    # Save configuration
    config.save_config('custom_rules.json')
    
    print("Configuration saved!")
    print(f"Java Callout Score: {config.rules['policies']['java_callout']}")