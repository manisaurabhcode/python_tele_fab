"""
Kong Configuration Generator Backend
Generates decK-compatible Kong configurations from Apigee proxies
"""

import json
import yaml
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import tempfile
import os
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate


@dataclass
class KongService:
    name: str
    url: str
    protocol: str = "https"
    port: int = 443
    path: str = "/"
    retries: int = 5
    connect_timeout: int = 60000
    write_timeout: int = 60000
    read_timeout: int = 60000


@dataclass
class KongRoute:
    name: str
    service: str
    protocols: List[str]
    paths: List[str]
    methods: Optional[List[str]] = None
    strip_path: bool = True
    preserve_host: bool = False


@dataclass
class KongPlugin:
    name: str
    service: Optional[str] = None
    route: Optional[str] = None
    enabled: bool = True
    config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass
class MigrationCoverage:
    total_policies: int
    migrated_policies: int
    manual_policies: int
    not_required_policies: int
    coverage_percentage: float
    
    
@dataclass
class BreakingChange:
    category: str
    description: str
    impact: str  # high, medium, low
    mitigation: str


class ApigeeToKongConverter:
    """Converts Apigee configurations to Kong decK format"""
    
    POLICY_MAPPINGS = {
        'VerifyAPIKey': {
            'plugin': 'key-auth',
            'auto_migrate': True,
            'config_mapper': 'map_key_auth'
        },
        'Quota': {
            'plugin': 'rate-limiting',
            'auto_migrate': True,
            'config_mapper': 'map_quota_to_rate_limit'
        },
        'SpikeArrest': {
            'plugin': 'rate-limiting',
            'auto_migrate': True,
            'config_mapper': 'map_spike_arrest'
        },
        'OAuthV2': {
            'plugin': 'oauth2',
            'auto_migrate': False,
            'config_mapper': 'map_oauth'
        },
        'CORS': {
            'plugin': 'cors',
            'auto_migrate': True,
            'config_mapper': 'map_cors'
        },
        'AssignMessage': {
            'plugin': 'request-transformer',
            'auto_migrate': True,
            'config_mapper': 'map_assign_message'
        },
        'ResponseCache': {
            'plugin': 'proxy-cache',
            'auto_migrate': True,
            'config_mapper': 'map_response_cache'
        },
        'MessageLogging': {
            'plugin': 'file-log',
            'auto_migrate': True,
            'config_mapper': 'map_message_logging'
        },
        'BasicAuthentication': {
            'plugin': 'basic-auth',
            'auto_migrate': True,
            'config_mapper': 'map_basic_auth'
        },
        'XMLToJSON': {
            'plugin': 'request-transformer',
            'auto_migrate': False,
            'config_mapper': 'map_xml_to_json'
        },
        'JSONToXML': {
            'plugin': 'response-transformer',
            'auto_migrate': False,
            'config_mapper': 'map_json_to_xml'
        },
        'Javascript': {
            'plugin': 'pre-function',
            'auto_migrate': False,
            'config_mapper': 'map_javascript'
        },
        'JavaCallout': {
            'plugin': 'custom',
            'auto_migrate': False,
            'config_mapper': None
        },
        'ServiceCallout': {
            'plugin': 'http-service',
            'auto_migrate': False,
            'config_mapper': 'map_service_callout'
        }
    }
    
    NOT_REQUIRED_POLICIES = [
        'StatisticsCollector',
        'AccessEntity',
        'KeyValueMapOperations',
        'RaiseFault',
        'FlowCallout'
    ]
    
    def __init__(self, api_key: str = None):
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key or os.getenv('ANTHROPIC_API_KEY'),
            max_tokens=4000
        )
        
    def extract_apigee_config(self, zip_path: str) -> Dict[str, Any]:
        """Extract configuration from Apigee proxy bundle"""
        config = {
            'name': Path(zip_path).stem,
            'policies': [],
            'target_endpoints': [],
            'proxy_endpoints': [],
            'resources': {}
        }
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file_info in zip_ref.filelist:
                content = zip_ref.read(file_info.filename).decode('utf-8', errors='ignore')
                
                if file_info.filename.endswith('.xml'):
                    if 'policies/' in file_info.filename:
                        config['policies'].append(self._parse_policy_xml(content))
                    elif 'proxies/' in file_info.filename:
                        config['proxy_endpoints'].append(self._parse_proxy_endpoint(content))
                    elif 'targets/' in file_info.filename:
                        config['target_endpoints'].append(self._parse_target_endpoint(content))
                
                elif file_info.filename.endswith(('.js', '.py', '.java')):
                    config['resources'][file_info.filename] = content
        
        return config
    
    def _parse_policy_xml(self, xml_content: str) -> Dict[str, Any]:
        """Parse Apigee policy XML"""
        try:
            root = ET.fromstring(xml_content)
            policy_type = root.tag
            policy_name = root.get('name', 'unknown')
            
            return {
                'type': policy_type,
                'name': policy_name,
                'config': self._xml_to_dict(root),
                'xml': xml_content
            }
        except:
            return {'type': 'unknown', 'name': 'unknown', 'config': {}}
    
    def _parse_proxy_endpoint(self, xml_content: str) -> Dict[str, Any]:
        """Parse proxy endpoint configuration"""
        try:
            root = ET.fromstring(xml_content)
            return {
                'name': root.get('name', 'default'),
                'base_path': root.findtext('.//BasePath', '/'),
                'flows': self._extract_flows(root)
            }
        except:
            return {'name': 'default', 'base_path': '/', 'flows': []}
    
    def _parse_target_endpoint(self, xml_content: str) -> Dict[str, Any]:
        """Parse target endpoint configuration"""
        try:
            root = ET.fromstring(xml_content)
            url = root.findtext('.//HTTPTargetConnection/URL', '')
            
            return {
                'name': root.get('name', 'default'),
                'url': url,
                'ssl_enabled': 'https' in url.lower()
            }
        except:
            return {'name': 'default', 'url': '', 'ssl_enabled': True}
    
    def _extract_flows(self, root: ET.Element) -> List[Dict]:
        """Extract flows from endpoint"""
        flows = []
        for flow in root.findall('.//Flow'):
            flows.append({
                'name': flow.get('name', ''),
                'condition': flow.findtext('Condition', ''),
                'request_steps': [step.findtext('Name') for step in flow.findall('.//Request/Step')],
                'response_steps': [step.findtext('Name') for step in flow.findall('.//Response/Step')]
            })
        return flows
    
    def _xml_to_dict(self, element: ET.Element) -> Dict:
        """Convert XML element to dictionary"""
        result = {}
        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                result[child.tag] = self._xml_to_dict(child)
        return result
    
    def generate_kong_config(self, apigee_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Kong decK configuration from Apigee config"""
        
        # Create Kong service
        service = self._create_kong_service(apigee_config)
        
        # Create Kong routes
        routes = self._create_kong_routes(apigee_config, service.name)
        
        # Create Kong plugins
        plugins = self._create_kong_plugins(apigee_config, service.name)
        
        # Build decK configuration
        deck_config = {
            '_format_version': '3.0',
            '_transform': True,
            'services': [asdict(service)],
            'routes': [asdict(route) for route in routes],
            'plugins': [asdict(plugin) for plugin in plugins]
        }
        
        return deck_config
    
    def _create_kong_service(self, apigee_config: Dict[str, Any]) -> KongService:
        """Create Kong service from Apigee target endpoint"""
        target = apigee_config['target_endpoints'][0] if apigee_config['target_endpoints'] else {}
        url = target.get('url', 'https://api.example.com')
        
        # Parse URL
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        return KongService(
            name=apigee_config['name'].lower().replace(' ', '-'),
            url=url,
            protocol=parsed.scheme or 'https',
            port=parsed.port or (443 if parsed.scheme == 'https' else 80),
            path=parsed.path or '/'
        )
    
    def _create_kong_routes(self, apigee_config: Dict[str, Any], service_name: str) -> List[KongRoute]:
        """Create Kong routes from Apigee proxy endpoints"""
        routes = []
        
        for proxy_endpoint in apigee_config['proxy_endpoints']:
            base_path = proxy_endpoint.get('base_path', '/')
            
            route = KongRoute(
                name=f"{service_name}-route",
                service=service_name,
                protocols=['https', 'http'],
                paths=[base_path],
                strip_path=True
            )
            routes.append(route)
        
        return routes
    
    def _create_kong_plugins(self, apigee_config: Dict[str, Any], service_name: str) -> List[KongPlugin]:
        """Create Kong plugins from Apigee policies"""
        plugins = []
        
        for policy in apigee_config['policies']:
            policy_type = policy['type']
            
            if policy_type in self.POLICY_MAPPINGS:
                mapping = self.POLICY_MAPPINGS[policy_type]
                
                if mapping['auto_migrate'] and mapping['config_mapper']:
                    config_method = getattr(self, mapping['config_mapper'], None)
                    if config_method:
                        plugin_config = config_method(policy['config'])
                        
                        plugin = KongPlugin(
                            name=mapping['plugin'],
                            service=service_name,
                            enabled=True,
                            config=plugin_config
                        )
                        plugins.append(plugin)
        
        return plugins
    
    # Configuration mappers
    def map_key_auth(self, apigee_config: Dict) -> Dict:
        """Map VerifyAPIKey to key-auth plugin"""
        return {
            'key_names': ['apikey', 'api-key', 'api_key'],
            'key_in_header': True,
            'key_in_query': True,
            'hide_credentials': True
        }
    
    def map_quota_to_rate_limit(self, apigee_config: Dict) -> Dict:
        """Map Quota to rate-limiting plugin"""
        interval = apigee_config.get('Interval', '1')
        time_unit = apigee_config.get('TimeUnit', 'minute')
        allow = apigee_config.get('Allow', '100')
        
        time_mapping = {
            'second': 'second',
            'minute': 'minute',
            'hour': 'hour',
            'day': 'day'
        }
        
        return {
            'minute': int(allow) if time_unit == 'minute' else None,
            'hour': int(allow) if time_unit == 'hour' else None,
            'day': int(allow) if time_unit == 'day' else None,
            'policy': 'local',
            'fault_tolerant': True
        }
    
    def map_spike_arrest(self, apigee_config: Dict) -> Dict:
        """Map SpikeArrest to rate-limiting plugin"""
        rate = apigee_config.get('Rate', '100ps')
        
        # Parse rate (e.g., "100ps" = 100 per second)
        import re
        match = re.match(r'(\d+)([a-z]+)', rate.lower())
        if match:
            limit, unit = match.groups()
            
            return {
                'second': int(limit) if unit.startswith('s') else None,
                'minute': int(limit) if unit.startswith('m') else None,
                'policy': 'local'
            }
        
        return {'second': 100}
    
    def map_cors(self, apigee_config: Dict) -> Dict:
        """Map CORS policy"""
        return {
            'origins': ['*'],
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
            'headers': ['Accept', 'Authorization', 'Content-Type'],
            'exposed_headers': ['X-Auth-Token'],
            'credentials': True,
            'max_age': 3600
        }
    
    def map_assign_message(self, apigee_config: Dict) -> Dict:
        """Map AssignMessage to request-transformer"""
        config = {
            'add': {'headers': [], 'querystring': []},
            'remove': {'headers': [], 'querystring': []},
            'replace': {'headers': []}
        }
        
        # Parse headers to add/remove
        if 'Add' in apigee_config:
            headers = apigee_config['Add'].get('Headers', {})
            for header, value in headers.items():
                config['add']['headers'].append(f"{header}:{value}")
        
        return config
    
    def map_response_cache(self, apigee_config: Dict) -> Dict:
        """Map ResponseCache to proxy-cache plugin"""
        return {
            'strategy': 'memory',
            'cache_ttl': 300,
            'content_type': ['application/json', 'text/plain'],
            'cache_control': False
        }
    
    def map_message_logging(self, apigee_config: Dict) -> Dict:
        """Map MessageLogging to file-log plugin"""
        return {
            'path': '/tmp/kong-logs.log',
            'reopen': True
        }
    
    def map_basic_auth(self, apigee_config: Dict) -> Dict:
        """Map BasicAuthentication to basic-auth plugin"""
        return {
            'hide_credentials': True
        }
    
    def map_xml_to_json(self, apigee_config: Dict) -> Dict:
        """Map XMLToJSON - requires custom plugin"""
        return {
            'note': 'Requires custom Lua plugin for XML to JSON transformation'
        }
    
    def map_json_to_xml(self, apigee_config: Dict) -> Dict:
        """Map JSONToXML - requires custom plugin"""
        return {
            'note': 'Requires custom Lua plugin for JSON to XML transformation'
        }
    
    def map_javascript(self, apigee_config: Dict) -> Dict:
        """Map Javascript callout - requires Lua conversion"""
        return {
            'note': 'JavaScript logic must be converted to Lua',
            'phase': 'access'
        }
    
    def map_service_callout(self, apigee_config: Dict) -> Dict:
        """Map ServiceCallout - may need custom plugin"""
        return {
            'note': 'May require custom plugin for complex service callout scenarios'
        }
    
    def calculate_coverage(self, apigee_config: Dict[str, Any]) -> MigrationCoverage:
        """Calculate migration coverage percentage"""
        total = len(apigee_config['policies'])
        migrated = 0
        manual = 0
        not_required = 0
        
        for policy in apigee_config['policies']:
            policy_type = policy['type']
            
            if policy_type in self.NOT_REQUIRED_POLICIES:
                not_required += 1
            elif policy_type in self.POLICY_MAPPINGS:
                if self.POLICY_MAPPINGS[policy_type]['auto_migrate']:
                    migrated += 1
                else:
                    manual += 1
        
        coverage = (migrated / total * 100) if total > 0 else 0
        
        return MigrationCoverage(
            total_policies=total,
            migrated_policies=migrated,
            manual_policies=manual,
            not_required_policies=not_required,
            coverage_percentage=round(coverage, 2)
        )
    
    def identify_breaking_changes(self, apigee_config: Dict[str, Any]) -> List[BreakingChange]:
        """Identify potential breaking changes"""
        changes = []
        
        # Check for JavaScript/Java callouts
        for policy in apigee_config['policies']:
            if policy['type'] in ['Javascript', 'JavaCallout']:
                changes.append(BreakingChange(
                    category='Custom Code Migration',
                    description=f"{policy['type']} policy '{policy['name']}' must be rewritten in Lua or Go",
                    impact='high',
                    mitigation='Review JavaScript/Java logic and convert to Kong-compatible Lua plugin'
                ))
        
        # Check for complex transformations
        for policy in apigee_config['policies']:
            if policy['type'] in ['XMLToJSON', 'JSONToXML', 'XSLTransform']:
                changes.append(BreakingChange(
                    category='Data Transformation',
                    description=f"Complex transformation in '{policy['name']}' may not have direct equivalent",
                    impact='medium',
                    mitigation='Implement custom transformation logic in Lua or use Kong plugin marketplace'
                ))
        
        # Check for OAuth complexity
        for policy in apigee_config['policies']:
            if policy['type'] == 'OAuthV2':
                changes.append(BreakingChange(
                    category='Authentication',
                    description='OAuth2 configuration requires manual review and testing',
                    impact='high',
                    mitigation='Review OAuth flows, scopes, and token validation logic carefully'
                ))
        
        # Check for service callouts
        for policy in apigee_config['policies']:
            if policy['type'] == 'ServiceCallout':
                changes.append(BreakingChange(
                    category='External Service Calls',
                    description='ServiceCallout may require custom plugin for complex scenarios',
                    impact='medium',
                    mitigation='Evaluate if Kong upstream service or custom plugin is needed'
                ))
        
        return changes
    
    async def generate_migration_report(
        self,
        apigee_config: Dict[str, Any],
        coverage: MigrationCoverage,
        breaking_changes: List[BreakingChange]
    ) -> str:
        """Generate comprehensive migration report using Claude"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert in API gateway migrations, specializing in Apigee to Kong migrations."),
            ("user", """Generate a comprehensive migration report based on the following information:

**Apigee Configuration:**
- Total Policies: {total_policies}
- Policy Types: {policy_types}
- Target Endpoints: {target_count}

**Migration Coverage:**
- Auto-migrated: {migrated} policies
- Manual migration required: {manual} policies
- Not required: {not_required} policies
- Coverage Percentage: {coverage}%

**Breaking Changes Identified:**
{breaking_changes}

Generate a detailed markdown report with these sections:
1. Executive Summary
2. Migration Coverage Analysis
3. Breaking Changes & Impact Assessment
4. Must-Change Items (Critical)
5. Recommended Changes (Best Practices)
6. Next Steps & Action Items
7. Risk Assessment
8. Testing Strategy
9. Rollback Plan
10. Timeline Estimate

Be specific, actionable, and include code examples where relevant.""")
        ])
        
        policy_types = [p['type'] for p in apigee_config['policies']]
        breaking_changes_text = "\n".join([
            f"- {bc.category}: {bc.description} (Impact: {bc.impact})"
            for bc in breaking_changes
        ])
        
        messages = prompt.format_messages(
            total_policies=len(apigee_config['policies']),
            policy_types=", ".join(set(policy_types)),
            target_count=len(apigee_config['target_endpoints']),
            migrated=coverage.migrated_policies,
            manual=coverage.manual_policies,
            not_required=coverage.not_required_policies,
            coverage=coverage.coverage_percentage,
            breaking_changes=breaking_changes_text
        )
        
        response = await self.llm.ainvoke(messages)
        return response.content


# Flask API
app = Flask(__name__)
CORS(app)

converter = ApigeeToKongConverter()


@app.route('/api/generate-kong-config', methods=['POST'])
async def generate_kong_config():
    """Generate Kong decK configuration from Apigee proxy"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        # Save temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        file.save(temp_file.name)
        
        # Extract Apigee config
        apigee_config = converter.extract_apigee_config(temp_file.name)
        
        # Generate Kong config
        kong_config = converter.generate_kong_config(apigee_config)
        
        # Calculate coverage
        coverage = converter.calculate_coverage(apigee_config)
        
        # Identify breaking changes
        breaking_changes = converter.identify_breaking_changes(apigee_config)
        
        # Generate migration report
        migration_report = await converter.generate_migration_report(
            apigee_config,
            coverage,
            breaking_changes
        )
        
        # Clean up
        os.unlink(temp_file.name)
        
        return jsonify({
            'kong_config': kong_config,
            'coverage': asdict(coverage),
            'breaking_changes': [asdict(bc) for bc in breaking_changes],
            'migration_report': migration_report
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export-deck-config', methods=['POST'])
def export_deck_config():
    """Export Kong configuration as YAML file for decK"""
    try:
        kong_config = request.json.get('kong_config')
        
        # Create YAML file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.yaml'
        )
        yaml.dump(kong_config, temp_file, default_flow_style=False, sort_keys=False)
        temp_file.close()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name='kong-config.yaml',
            mimetype='application/x-yaml'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export-migration-report', methods=['POST'])
def export_migration_report():
    """Export migration report as Markdown file"""
    try:
        report = request.json.get('migration_report')
        
        # Create Markdown file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.md'
        )
        temp_file.write(report)
        temp_file.close()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name='migration-report.md',
            mimetype='text/markdown'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)