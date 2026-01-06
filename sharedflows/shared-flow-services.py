# services/shared_flow_analyzer.py
"""
Analyzer for Apigee Shared Flows
Understands shared flow structure, policies, and reusability patterns
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import json


class SharedFlowAnalyzer:
    """Analyze Apigee Shared Flow bundles and determine Kong migration strategy"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def analyze(self, bundle: Dict[str, Any], scoring_rules: Dict = None) -> Dict[str, Any]:
        """
        Analyze shared flow bundle and determine migration approach.
        
        Args:
            bundle: Extracted shared flow bundle with xml_files, code_files
            scoring_rules: Optional scoring rules for policy evaluation
            
        Returns:
            Analysis dict with policies, structure, and migration recommendations
        """
        xml_files = bundle.get('xml_files', {})
        code_files = bundle.get('code_files', {})
        
        # Parse shared flow definition
        shared_flow_def = self._parse_shared_flow_definition(xml_files)
        
        # Extract policies
        policies = self._extract_policies(xml_files)
        
        # Analyze flow hooks and attachment points
        flow_structure = self._analyze_flow_structure(shared_flow_def)
        
        # Determine if this should be a Kong plugin or service template
        recommendation = self._recommend_migration_approach(policies, flow_structure, code_files)
        
        # Use LLM for deeper analysis
        llm_analysis = self._llm_analyze_shared_flow(shared_flow_def, policies, code_files)
        
        analysis = {
            'shared_flow_name': shared_flow_def.get('name', 'unknown'),
            'shared_flow_type': 'reusable_flow',
            'policies': policies,
            'flow_structure': flow_structure,
            'recommended_approach': recommendation['approach'],
            'migration_strategy': recommendation['strategy'],
            'reusability_score': recommendation['reusability_score'],
            'can_be_kong_plugin': recommendation['can_be_plugin'],
            'code_files': list(code_files.keys()),
            'complexity': self._calculate_complexity(policies, code_files),
            'llm_insights': llm_analysis,
            'scoring': self._apply_scoring_rules(policies, scoring_rules or {})
        }
        
        return analysis
    
    def _parse_shared_flow_definition(self, xml_files: Dict[str, str]) -> Dict[str, Any]:
        """Parse the main shared flow definition XML"""
        shared_flow_data = {
            'name': 'unknown',
            'flows': [],
            'policies_attached': []
        }
        
        # Look for SharedFlowBundle or SharedFlow XML
        for filename, content in xml_files.items():
            if 'sharedflow' in filename.lower() or filename.endswith('.xml'):
                try:
                    root = ET.fromstring(content)
                    
                    # Get name
                    if root.get('name'):
                        shared_flow_data['name'] = root.get('name')
                    
                    # Extract flows
                    for flow in root.findall('.//Flow'):
                        flow_name = flow.get('name', 'default')
                        steps = []
                        
                        for step in flow.findall('.//Step'):
                            step_name = step.find('Name')
                            condition = step.find('Condition')
                            steps.append({
                                'name': step_name.text if step_name is not None else 'unknown',
                                'condition': condition.text if condition is not None else None
                            })
                        
                        shared_flow_data['flows'].append({
                            'name': flow_name,
                            'steps': steps
                        })
                    
                    # Extract policy attachments
                    for step in root.findall('.//Step'):
                        name_elem = step.find('Name')
                        if name_elem is not None:
                            shared_flow_data['policies_attached'].append(name_elem.text)
                    
                except ET.ParseError as e:
                    print(f"XML Parse error for {filename}: {e}")
                    continue
        
        return shared_flow_data
    
    def _extract_policies(self, xml_files: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract all policies from the shared flow"""
        policies = []
        
        for filename, content in xml_files.items():
            # Skip the main shared flow definition
            if 'sharedflow' in filename.lower():
                continue
            
            try:
                root = ET.fromstring(content)
                policy_type = root.tag
                policy_name = root.get('name', filename.replace('.xml', ''))
                
                # Extract policy configuration
                config = {}
                for elem in root:
                    if elem.text and elem.text.strip():
                        config[elem.tag] = elem.text.strip()
                    elif len(elem) > 0:
                        config[elem.tag] = self._xml_to_dict(elem)
                
                policies.append({
                    'name': policy_name,
                    'type': policy_type,
                    'config': config,
                    'filename': filename
                })
                
            except ET.ParseError:
                continue
        
        return policies
    
    def _xml_to_dict(self, element) -> Dict:
        """Convert XML element to dictionary"""
        result = {}
        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                result[child.tag] = self._xml_to_dict(child)
        return result
    
    def _analyze_flow_structure(self, shared_flow_def: Dict) -> Dict[str, Any]:
        """Analyze the flow structure and attachment patterns"""
        structure = {
            'total_flows': len(shared_flow_def.get('flows', [])),
            'total_steps': sum(len(f.get('steps', [])) for f in shared_flow_def.get('flows', [])),
            'conditional_steps': 0,
            'flow_names': []
        }
        
        for flow in shared_flow_def.get('flows', []):
            structure['flow_names'].append(flow.get('name'))
            for step in flow.get('steps', []):
                if step.get('condition'):
                    structure['conditional_steps'] += 1
        
        return structure
    
    def _recommend_migration_approach(
        self, 
        policies: List[Dict], 
        flow_structure: Dict,
        code_files: Dict
    ) -> Dict[str, Any]:
        """
        Recommend whether this shared flow should become:
        - A Kong plugin (reusable, complex logic)
        - A service template (simple, configuration-based)
        - Multiple plugins (if too complex)
        """
        
        # Scoring factors
        policy_count = len(policies)
        has_custom_code = len(code_files) > 0
        complexity = flow_structure['conditional_steps']
        
        # Calculate reusability score (0-100)
        reusability_score = min(100, (
            (policy_count * 10) +
            (has_custom_code * 20) +
            (complexity * 5)
        ))
        
        # Determine approach
        if reusability_score > 60 or has_custom_code:
            approach = 'plugin'
            strategy = 'Create a custom Kong plugin for maximum reusability'
            can_be_plugin = True
        elif policy_count <= 3 and not has_custom_code:
            approach = 'service_template'
            strategy = 'Use Kong service/route configuration template'
            can_be_plugin = False
        else:
            approach = 'hybrid'
            strategy = 'Combine Kong plugins with service configuration'
            can_be_plugin = True
        
        return {
            'approach': approach,
            'strategy': strategy,
            'reusability_score': reusability_score,
            'can_be_plugin': can_be_plugin
        }
    
    def _calculate_complexity(self, policies: List[Dict], code_files: Dict) -> str:
        """Calculate complexity: low, medium, high"""
        score = len(policies) + (len(code_files) * 3)
        
        if score <= 5:
            return 'low'
        elif score <= 15:
            return 'medium'
        else:
            return 'high'
    
    def _apply_scoring_rules(self, policies: List[Dict], rules: Dict) -> Dict:
        """Apply scoring rules to policies"""
        scores = {}
        for policy in policies:
            policy_type = policy['type']
            if policy_type in rules:
                scores[policy['name']] = rules[policy_type]
        return scores
    
    def _llm_analyze_shared_flow(
        self, 
        shared_flow_def: Dict, 
        policies: List[Dict],
        code_files: Dict
    ) -> Dict[str, Any]:
        """Use LLM to provide deeper insights about the shared flow"""
        
        prompt = f"""Analyze this Apigee Shared Flow and provide migration insights for Kong Gateway.

Shared Flow Name: {shared_flow_def.get('name')}
Number of Policies: {len(policies)}
Policies: {', '.join([p['type'] for p in policies])}
Has Custom Code: {len(code_files) > 0}

Provide:
1. Key functionality of this shared flow
2. Best Kong migration approach (plugin vs template)
3. Potential challenges in migration
4. Reusability recommendations

Keep response concise and actionable."""
        
        try:
            response = self.llm.generate(prompt)
            return {
                'insights': response,
                'analyzed_with_llm': True
            }
        except Exception as e:
            return {
                'insights': f'LLM analysis unavailable: {str(e)}',
                'analyzed_with_llm': False
            }


# services/shared_flow_generator.py
"""
Generate Kong Gateway configuration from Apigee Shared Flow analysis
"""

import yaml
from typing import Dict, Any, List


class SharedFlowKongGenerator:
    """Generate Kong configuration from shared flow analysis"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        
        # Policy to Kong plugin mapping
        self.policy_mappings = {
            'SpikeArrest': 'rate-limiting',
            'Quota': 'rate-limiting',
            'VerifyAPIKey': 'key-auth',
            'OAuthV2': 'oauth2',
            'BasicAuthentication': 'basic-auth',
            'CORS': 'cors',
            'AssignMessage': 'request-transformer',
            'RaiseFault': 'request-termination',
            'MessageLogging': 'file-log',
            'Statistics': 'prometheus',
            'JSONThreatProtection': 'custom-json-threat',
            'XMLThreatProtection': 'custom-xml-threat'
        }
    
    def generate(self, analysis: Dict[str, Any]) -> str:
        """
        Generate Kong configuration YAML from shared flow analysis.
        
        Args:
            analysis: Shared flow analysis from SharedFlowAnalyzer
            
        Returns:
            Kong declarative configuration as YAML string
        """
        approach = analysis.get('recommended_approach', 'plugin')
        
        if approach == 'plugin':
            return self._generate_plugin_config(analysis)
        elif approach == 'service_template':
            return self._generate_service_template(analysis)
        else:
            return self._generate_hybrid_config(analysis)
    
    def _generate_plugin_config(self, analysis: Dict) -> str:
        """Generate Kong plugin configuration"""
        shared_flow_name = analysis.get('shared_flow_name', 'shared_flow')
        plugin_name = shared_flow_name.lower().replace(' ', '_').replace('-', '_')
        policies = analysis.get('policies', [])
        
        # Use LLM to generate plugin configuration
        prompt = f"""Generate Kong declarative configuration (decK YAML) for this Apigee Shared Flow.

Shared Flow: {shared_flow_name}
Policies: {', '.join([p['type'] for p in policies])}
Approach: Custom Kong Plugin

Generate a complete Kong plugin configuration that can be reused across services.
Include plugin schema and default configuration.
Output only valid YAML, no explanations."""
        
        try:
            llm_config = self.llm.generate(prompt)
            return llm_config
        except Exception:
            # Fallback to template-based generation
            return self._fallback_plugin_config(analysis)
    
    def _generate_service_template(self, analysis: Dict) -> str:
        """Generate Kong service template configuration"""
        shared_flow_name = analysis.get('shared_flow_name', 'shared_flow')
        policies = analysis.get('policies', [])
        
        config = {
            '_format_version': '3.0',
            '_comment': f'Kong service template from Apigee Shared Flow: {shared_flow_name}',
            'services': [{
                'name': f'{shared_flow_name.lower().replace(" ", "-")}-service',
                'url': 'http://backend:8080',
                'routes': [{
                    'name': f'{shared_flow_name.lower().replace(" ", "-")}-route',
                    'paths': ['/api'],
                    'methods': ['GET', 'POST', 'PUT', 'DELETE']
                }],
                'plugins': []
            }]
        }
        
        # Add Kong plugins based on Apigee policies
        for policy in policies:
            kong_plugin = self._map_policy_to_plugin(policy)
            if kong_plugin:
                config['services'][0]['plugins'].append(kong_plugin)
        
        return yaml.dump(config, default_flow_style=False, sort_keys=False)
    
    def _generate_hybrid_config(self, analysis: Dict) -> str:
        """Generate hybrid configuration (plugins + templates)"""
        return self._generate_service_template(analysis)
    
    def _map_policy_to_plugin(self, policy: Dict) -> Dict[str, Any]:
        """Map Apigee policy to Kong plugin configuration"""
        policy_type = policy.get('type')
        kong_plugin_name = self.policy_mappings.get(policy_type)
        
        if not kong_plugin_name:
            return None
        
        plugin_config = {
            'name': kong_plugin_name,
            'enabled': True,
            'config': {}
        }
        
        # Policy-specific configuration
        if policy_type == 'SpikeArrest':
            rate = policy.get('config', {}).get('Rate', '10ps')
            limit = int(rate.replace('ps', '').replace('pm', ''))
            plugin_config['config'] = {'second': limit}
        
        elif policy_type == 'VerifyAPIKey':
            plugin_config['config'] = {
                'key_names': ['apikey', 'api-key'],
                'hide_credentials': True
            }
        
        elif policy_type == 'CORS':
            plugin_config['config'] = {
                'origins': ['*'],
                'methods': ['GET', 'POST', 'PUT', 'DELETE'],
                'headers': ['Accept', 'Content-Type', 'Authorization'],
                'credentials': True
            }
        
        return plugin_config
    
    def _fallback_plugin_config(self, analysis: Dict) -> str:
        """Fallback plugin configuration if LLM fails"""
        shared_flow_name = analysis.get('shared_flow_name', 'shared_flow')
        plugin_name = shared_flow_name.lower().replace(' ', '_')
        
        config = {
            '_format_version': '3.0',
            'plugins': [{
                'name': plugin_name,
                'enabled': True,
                'config': {
                    'shared_flow_name': shared_flow_name,
                    'description': f'Custom plugin from Apigee Shared Flow: {shared_flow_name}'
                }
            }]
        }
        
        return yaml.dump(config, default_flow_style=False)
    
    def generate_plugin_spec(self, analysis: Dict) -> Dict[str, Any]:
        """Generate plugin specification for PluginBuilder"""
        shared_flow_name = analysis.get('shared_flow_name', 'shared_flow')
        policies = analysis.get('policies', [])
        
        spec = {
            'plugin_name': shared_flow_name.lower().replace(' ', '_'),
            'description': f'Kong plugin migrated from Apigee Shared Flow: {shared_flow_name}',
            'policies': [p['type'] for p in policies],
            'has_custom_logic': len(analysis.get('code_files', [])) > 0,
            'complexity': analysis.get('complexity', 'medium'),
            'priority': 1000
        }
        
        return spec
    
    def generate_integration_guide(
        self, 
        analysis: Dict, 
        kong_config: str,
        plugins: Dict[str, str]
    ) -> str:
        """Generate integration guide for applying shared flow to proxies"""
        
        shared_flow_name = analysis.get('shared_flow_name', 'shared_flow')
        approach = analysis.get('recommended_approach', 'plugin')
        
        guide = f"""# Integration Guide: {shared_flow_name}

## Overview
This shared flow has been migrated to Kong Gateway as a **{approach}**.

## Migration Approach
{analysis.get('migration_strategy', 'See documentation for details')}

## Reusability Score
{analysis.get('reusability_score', 0)}/100

## How to Apply to Your Proxies

### Option 1: Apply as Kong Plugin
```yaml
# Add to any Kong service
services:
  - name: your-service
    plugins:
      - name: {shared_flow_name.lower().replace(' ', '_')}
        enabled: true
        config:
          # Plugin configuration here
```

### Option 2: Apply to Specific Routes
```yaml
# Add to specific routes
routes:
  - name: your-route
    plugins:
      - name: {shared_flow_name.lower().replace(' ', '_')}
        enabled: true
```

### Option 3: Global Application
```yaml
# Apply globally to all services
plugins:
  - name: {shared_flow_name.lower().replace(' ', '_')}
    enabled: true
```

## Custom Plugins
{len(plugins)} custom plugin(s) generated:
{chr(10).join([f'- {name}' for name in plugins.keys()])}

## Testing
After applying the configuration:
1. Deploy custom plugins to Kong
2. Apply configuration with decK
3. Test endpoints
4. Monitor Kong logs

## Policies Migrated
{chr(10).join([f'- {p["type"]}: {p["name"]}' for p in analysis.get('policies', [])])}

## Next Steps
1. Review generated Kong configuration
2. Deploy custom plugins (if any)
3. Apply to your Kong services/routes
4. Run integration tests
5. Monitor and validate behavior
"""
        
        return guide
    
    def combine_configurations(
        self,
        proxy_config: str,
        shared_flow_configs: List[str],
        proxy_analysis: Dict,
        shared_flow_analyses: List[Dict]
    ) -> str:
        """
        Combine proxy and shared flow configurations into a single Kong config.
        
        Args:
            proxy_config: Kong config from proxy migration
            shared_flow_configs: List of Kong configs from shared flows
            proxy_analysis: Proxy analysis
            shared_flow_analyses: List of shared flow analyses
            
        Returns:
            Combined Kong configuration YAML
        """
        
        try:
            # Parse existing configurations
            proxy_dict = yaml.safe_load(proxy_config)
            sf_dicts = [yaml.safe_load(sf) for sf in shared_flow_configs]
            
            # Extract plugins from shared flows
            all_sf_plugins = []
            for sf_dict in sf_dicts:
                if 'plugins' in sf_dict:
                    all_sf_plugins.extend(sf_dict['plugins'])
            
            # Add shared flow plugins to proxy services
            if 'services' in proxy_dict:
                for service in proxy_dict['services']:
                    if 'plugins' not in service:
                        service['plugins'] = []
                    service['plugins'].extend(all_sf_plugins)
            
            # Add global plugins if any
            if 'plugins' not in proxy_dict:
                proxy_dict['plugins'] = []
            proxy_dict['plugins'].extend(all_sf_plugins)
            
            # Add comment
            proxy_dict['_comment'] = f'Combined configuration: {proxy_analysis.get("proxy_name")} + {len(shared_flow_analyses)} shared flow(s)'
            
            return yaml.dump(proxy_dict, default_flow_style=False, sort_keys=False)
            
        except Exception as e:
            # Fallback: concatenate configurations
            return f"{proxy_config}\n\n# Shared Flow Configurations\n{chr(10).join(shared_flow_configs)}"
