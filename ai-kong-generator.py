"""
AI-Driven Kong Configuration Generator
Fully AI-powered Apigee to Kong migration with intelligent policy bundling
"""

import json
import yaml
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import tempfile
import os
import re
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


# ============================================
# Data Models
# ============================================

class PolicyMapping(BaseModel):
    """AI-generated policy mapping"""
    apigee_policy: str
    apigee_policy_type: str
    kong_solution: str
    kong_plugin: Optional[str] = None
    bundled_with: List[str] = Field(default_factory=list)
    auto_generated: bool
    confidence: float
    requires_custom_plugin: bool
    custom_plugin_name: Optional[str] = None
    reasoning: str


class MigrationCoverage(BaseModel):
    """Detailed migration coverage analysis"""
    total_policies: int
    auto_migrated: int
    bundled_policies: int
    requires_custom_plugin: int
    not_required: int
    coverage_percentage: float
    bundling_efficiency: float
    policy_details: List[PolicyMapping]


class ManualStep(BaseModel):
    """Manual migration step"""
    step_number: int
    category: str
    title: str
    description: str
    priority: str  # critical, high, medium, low
    estimated_time: str
    commands: List[str] = Field(default_factory=list)
    code_snippets: Dict[str, str] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Configuration validation result"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class MigrationPackage(BaseModel):
    """Complete migration package"""
    kong_config: Dict[str, Any]
    custom_plugins: Dict[str, str] = Field(default_factory=dict)
    coverage: MigrationCoverage
    manual_steps: List[ManualStep]
    validation: ValidationResult
    migration_report: str
    test_scripts: str


# ============================================
# AI-Driven Kong Generator
# ============================================

class AIKongGenerator:
    """Fully AI-driven Kong configuration generator"""
    
    def __init__(self, api_key: str = None):
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key or os.getenv('ANTHROPIC_API_KEY'),
            max_tokens=16000,
            temperature=0.1  # Low temperature for consistent technical output
        )
        
    def extract_apigee_files(self, zip_path: str) -> Dict[str, Any]:
        """Extract all relevant files from Apigee proxy bundle"""
        extracted = {
            'proxy_name': Path(zip_path).stem,
            'xml_files': {},
            'code_files': {},
            'config_files': {}
        }
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.is_dir():
                        continue
                    
                    content = zip_ref.read(file_info.filename).decode('utf-8', errors='ignore')
                    filename = file_info.filename
                    
                    if filename.endswith('.xml'):
                        extracted['xml_files'][filename] = content
                    elif filename.endswith(('.js', '.java', '.py')):
                        extracted['code_files'][filename] = content
                    elif filename.endswith(('.json', '.properties')):
                        extracted['config_files'][filename] = content
                        
        except Exception as e:
            print(f"Error extracting {zip_path}: {e}")
            
        return extracted
    
    async def analyze_apigee_proxy(self, apigee_files: Dict[str, Any]) -> str:
        """Phase 1: AI analyzes Apigee proxy to understand complete behavior"""
        
        # Prepare content for AI analysis
        xml_content = "\n\n".join([
            f"## File: {fname}\n```xml\n{content[:2000]}\n```"
            for fname, content in apigee_files['xml_files'].items()
        ])
        
        code_content = "\n\n".join([
            f"## File: {fname}\n```{self._get_language(fname)}\n{content[:1500]}\n```"
            for fname, content in apigee_files['code_files'].items()
        ])
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in Apigee API Gateway with deep knowledge of API management patterns.
Analyze the provided Apigee proxy configuration comprehensively."""),
            ("user", """Analyze this Apigee proxy bundle and provide a detailed understanding:

**Proxy Name:** {proxy_name}

**XML Configuration Files:**
{xml_content}

**Code Files:**
{code_content}

Provide comprehensive analysis in JSON format:
{{
  "proxy_overview": {{
    "name": "proxy name",
    "base_path": "base path",
    "target_endpoint": "backend URL",
    "description": "what this proxy does"
  }},
  "policies_analysis": [
    {{
      "policy_name": "name",
      "policy_type": "type",
      "purpose": "what it does",
      "configuration": {{}},
      "dependencies": ["other policies it depends on"],
      "can_be_bundled": true/false,
      "bundling_candidates": ["policies that could be bundled together"]
    }}
  ],
  "custom_code_analysis": [
    {{
      "file": "filename",
      "purpose": "what it does",
      "complexity": "low/medium/high",
      "kong_approach": "how to handle in Kong"
    }}
  ],
  "flows": [
    {{
      "flow_name": "name",
      "condition": "when it runs",
      "policies": ["policy sequence"]
    }}
  ],
  "security": {{
    "authentication": "method used",
    "authorization": "authorization approach",
    "threat_protection": ["threat protection mechanisms"]
  }},
  "bundling_opportunities": [
    {{
      "bundle_name": "descriptive name",
      "policies": ["policy1", "policy2"],
      "reason": "why these should be bundled",
      "single_plugin": "Kong plugin that handles all"
    }}
  ]
}}""")
        ])
        
        messages = analysis_prompt.format_messages(
            proxy_name=apigee_files['proxy_name'],
            xml_content=xml_content or "No XML files",
            code_content=code_content or "No code files"
        )
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def generate_kong_config(self, analysis: str, apigee_files: Dict[str, Any]) -> str:
        """Phase 2: AI generates complete Kong decK configuration with intelligent bundling"""
        
        generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Kong Gateway expert specializing in decK declarative configurations.
Generate production-ready Kong configurations with intelligent policy bundling."""),
            ("user", """Based on this Apigee proxy analysis, generate a complete Kong decK configuration.

**Analysis:**
{analysis}

**Requirements:**
1. Generate valid decK YAML format (version 3.0)
2. Bundle multiple Apigee policies into single Kong plugins where possible
   - Example: VerifyAPIKey + Quota → key-auth + rate-limiting with consumer binding
   - Example: Multiple AssignMessage → single request-transformer with all transformations
3. Use appropriate Kong plugins for each policy
4. Preserve exact business logic and flow order
5. Include proper plugin priorities (higher number = runs earlier)
6. Configure plugin at appropriate level (service, route, consumer)
7. Add meaningful tags for tracking
8. Include comments explaining bundling decisions

**Kong Plugins Priority Reference:**
- Authentication: 1000-1100
- Security: 900-1000  
- Rate Limiting: 800-900
- Transformation: 700-800
- Logging: 600-700
- Custom: 500-600

**Output ONLY valid decK YAML with inline comments. No markdown, no explanations outside YAML comments.**

Example structure:
```yaml
_format_version: "3.0"
_transform: true

# Comments explaining bundling
services:
  - name: service-name
    # ... config

routes:
  - name: route-name
    # ... config

plugins:
  # Bundled: VerifyAPIKey + Quota policies
  - name: key-auth
    service: service-name
    # ... config
  
  - name: rate-limiting
    service: service-name
    consumer: {{consumer_id}}
    # ... config
```

Generate the complete configuration now:""")
        ])
        
        messages = generation_prompt.format_messages(analysis=analysis)
        response = await self.llm.ainvoke(messages)
        
        # Extract YAML from response
        yaml_content = self._extract_yaml(response.content)
        return yaml_content
    
    async def generate_custom_plugins(self, analysis: str, apigee_files: Dict[str, Any]) -> Dict[str, str]:
        """Phase 3: Generate custom Lua plugins for complex logic"""
        
        custom_plugins = {}
        
        # Check if custom code exists
        if not apigee_files['code_files']:
            return custom_plugins
        
        for filename, code_content in apigee_files['code_files'].items():
            plugin_name = self._generate_plugin_name(filename)
            
            plugin_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a Kong plugin developer expert in Lua programming.
Generate production-ready Kong plugins that replicate Apigee behavior."""),
                ("user", """Convert this Apigee code to a Kong Lua plugin.

**Apigee Analysis Context:**
{analysis}

**Original Code ({filename}):**
```
{code_content}
```

Generate THREE files in this exact format:

=== FILE: handler.lua ===
[complete handler.lua code]

=== FILE: schema.lua ===
[complete schema.lua code]

=== FILE: README.md ===
[installation and usage instructions]

**Requirements:**
1. Use Kong PDK (Plugin Development Kit) APIs
2. Handle errors gracefully
3. Include logging for debugging
4. Match Apigee behavior exactly
5. Add configuration options
6. Include inline comments

Generate all three files now:""")
            ])
            
            messages = plugin_prompt.format_messages(
                analysis=analysis[:2000],
                filename=filename,
                code_content=code_content[:3000]
            )
            
            response = await self.llm.ainvoke(messages)
            custom_plugins[plugin_name] = response.content
        
        return custom_plugins
    
    async def validate_configuration(self, kong_config: str, analysis: str) -> ValidationResult:
        """Phase 4: AI validates the generated configuration"""
        
        validation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Kong configuration validator expert.
Review configurations for correctness, security, and best practices."""),
            ("user", """Validate this Kong configuration against the original Apigee analysis.

**Original Apigee Analysis:**
{analysis}

**Generated Kong Configuration:**
```yaml
{kong_config}
```

Review for:
1. decK format compliance (version 3.0)
2. All Apigee policies covered
3. Correct plugin priorities
4. Security best practices
5. Performance considerations
6. Missing configurations
7. Potential issues

Provide validation in JSON format:
{{
  "is_valid": true/false,
  "errors": ["critical issues that must be fixed"],
  "warnings": ["non-critical issues to address"],
  "suggestions": ["optimization recommendations"],
  "missing_policies": ["Apigee policies not covered"],
  "security_concerns": ["security items to review"],
  "performance_notes": ["performance considerations"]
}}""")
        ])
        
        messages = validation_prompt.format_messages(
            analysis=analysis[:3000],
            kong_config=kong_config
        )
        
        response = await self.llm.ainvoke(messages)
        
        # Parse validation result
        validation_data = self._extract_json(response.content)
        
        return ValidationResult(
            is_valid=validation_data.get('is_valid', False),
            errors=validation_data.get('errors', []) + validation_data.get('missing_policies', []),
            warnings=validation_data.get('warnings', []) + validation_data.get('security_concerns', []),
            suggestions=validation_data.get('suggestions', []) + validation_data.get('performance_notes', [])
        )
    
    async def calculate_coverage(self, analysis: str, kong_config: str) -> MigrationCoverage:
        """Calculate detailed migration coverage with bundling analysis"""
        
        coverage_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a migration analyst expert. 
Analyze coverage and policy bundling efficiency."""),
            ("user", """Analyze migration coverage for this Apigee to Kong migration.

**Apigee Analysis:**
{analysis}

**Kong Configuration:**
{kong_config}

Provide detailed coverage analysis in JSON format:
{{
  "total_policies": <number>,
  "policy_mappings": [
    {{
      "apigee_policy": "policy name",
      "apigee_policy_type": "policy type",
      "kong_solution": "how it's handled",
      "kong_plugin": "plugin name or null",
      "bundled_with": ["other policies bundled together"],
      "auto_generated": true/false,
      "confidence": 0.0-1.0,
      "requires_custom_plugin": true/false,
      "custom_plugin_name": "name or null",
      "reasoning": "explanation"
    }}
  ],
  "bundling_analysis": {{
    "total_bundles": <number>,
    "bundled_policies_count": <number>,
    "efficiency_gain": "percentage of reduced plugin count"
  }},
  "not_required_policies": ["policies not needed in Kong"],
  "coverage_percentage": <0-100>
}}""")
        ])
        
        messages = coverage_prompt.format_messages(
            analysis=analysis[:4000],
            kong_config=kong_config[:4000]
        )
        
        response = await self.llm.ainvoke(messages)
        coverage_data = self._extract_json(response.content)
        
        # Build coverage model
        mappings = [PolicyMapping(**m) for m in coverage_data.get('policy_mappings', [])]
        
        total = coverage_data.get('total_policies', 0)
        auto = sum(1 for m in mappings if m.auto_generated)
        bundled = coverage_data.get('bundling_analysis', {}).get('bundled_policies_count', 0)
        custom = sum(1 for m in mappings if m.requires_custom_plugin)
        not_required = len(coverage_data.get('not_required_policies', []))
        
        coverage_pct = coverage_data.get('coverage_percentage', 0)
        bundling_efficiency = float(coverage_data.get('bundling_analysis', {}).get('efficiency_gain', '0').replace('%', ''))
        
        return MigrationCoverage(
            total_policies=total,
            auto_migrated=auto,
            bundled_policies=bundled,
            requires_custom_plugin=custom,
            not_required=not_required,
            coverage_percentage=coverage_pct,
            bundling_efficiency=bundling_efficiency,
            policy_details=mappings
        )
    
    async def generate_manual_steps(self, analysis: str, coverage: MigrationCoverage, 
                                   custom_plugins: Dict[str, str]) -> List[ManualStep]:
        """Generate detailed manual migration steps"""
        
        manual_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a migration guide expert.
Generate clear, actionable manual migration steps."""),
            ("user", """Generate detailed manual migration steps for this Apigee to Kong migration.

**Apigee Analysis:**
{analysis}

**Coverage Details:**
- Total Policies: {total_policies}
- Auto-migrated: {auto_migrated}
- Requires Custom Plugin: {custom_plugins_count}
- Not Required: {not_required}

**Custom Plugins Required:**
{custom_plugin_list}

Generate step-by-step manual instructions in JSON format:
[
  {{
    "step_number": 1,
    "category": "Authentication / Configuration / Testing / etc",
    "title": "Short descriptive title",
    "description": "Detailed description of what needs to be done",
    "priority": "critical/high/medium/low",
    "estimated_time": "30 minutes / 2 hours / etc",
    "commands": ["command1", "command2"],
    "code_snippets": {{
      "file.lua": "code content",
      "test.sh": "test script"
    }}
  }}
]

Include steps for:
1. API key migration (if applicable)
2. Custom plugin installation
3. Configuration testing
4. Security validation
5. Performance testing
6. Rollback preparation""")
        ])
        
        custom_plugin_list = "\n".join([f"- {name}" for name in custom_plugins.keys()]) or "None"
        
        messages = manual_prompt.format_messages(
            analysis=analysis[:3000],
            total_policies=coverage.total_policies,
            auto_migrated=coverage.auto_migrated,
            custom_plugins_count=coverage.requires_custom_plugin,
            not_required=coverage.not_required,
            custom_plugin_list=custom_plugin_list
        )
        
        response = await self.llm.ainvoke(messages)
        steps_data = self._extract_json(response.content)
        
        return [ManualStep(**step) for step in steps_data]
    
    async def generate_migration_report(self, analysis: str, coverage: MigrationCoverage,
                                       validation: ValidationResult, manual_steps: List[ManualStep]) -> str:
        """Generate comprehensive migration report"""
        
        report_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a technical documentation expert.
Generate comprehensive, actionable migration reports."""),
            ("user", """Generate a comprehensive migration report in Markdown format.

**Apigee Analysis:**
{analysis}

**Coverage:**
- Total Policies: {total_policies}
- Auto-migrated: {auto_migrated} ({coverage_pct}%)
- Bundled: {bundled_policies}
- Custom Plugins Required: {custom_required}
- Bundling Efficiency: {bundling_efficiency}%

**Validation Status:**
- Valid: {is_valid}
- Errors: {error_count}
- Warnings: {warning_count}

**Manual Steps Required:** {manual_step_count}

Generate a professional migration report with these sections:

# Executive Summary
# Migration Coverage Analysis
  ## Policy Mapping Details
  ## Bundling Optimization
# Breaking Changes & Impact
# Manual Migration Steps (Critical First)
# Testing Strategy
# Deployment Plan
# Rollback Procedure
# Risk Assessment
# Timeline Estimate
# Success Criteria

Be specific, actionable, and include code examples.""")
        ])
        
        messages = report_prompt.format_messages(
            analysis=analysis[:2000],
            total_policies=coverage.total_policies,
            auto_migrated=coverage.auto_migrated,
            coverage_pct=coverage.coverage_percentage,
            bundled_policies=coverage.bundled_policies,
            custom_required=coverage.requires_custom_plugin,
            bundling_efficiency=coverage.bundling_efficiency,
            is_valid=validation.is_valid,
            error_count=len(validation.errors),
            warning_count=len(validation.warnings),
            manual_step_count=len(manual_steps)
        )
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def generate_test_scripts(self, analysis: str, kong_config: str) -> str:
        """Generate comprehensive test scripts"""
        
        test_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a QA automation expert.
Generate comprehensive test scripts for API migrations."""),
            ("user", """Generate test scripts for this Kong migration.

**Apigee Analysis:**
{analysis}

**Kong Configuration:**
{kong_config}

Generate a complete bash test script that tests:
1. Authentication (API keys, OAuth, etc.)
2. Rate limiting
3. CORS
4. Request/response transformations
5. Error handling
6. Performance (basic load test)

Include:
- Setup commands
- Individual test cases with assertions
- Cleanup commands
- Results summary

Output as executable bash script with comments.""")
        ])
        
        messages = test_prompt.format_messages(
            analysis=analysis[:2000],
            kong_config=kong_config[:2000]
        )
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def generate_complete_migration(self, zip_path: str) -> MigrationPackage:
        """
        Main method: Generate complete migration package
        """
        print("🚀 Starting AI-driven migration...")
        
        # Phase 1: Extract files
        print("📦 Extracting Apigee proxy bundle...")
        apigee_files = self.extract_apigee_files(zip_path)
        
        # Phase 2: AI Analysis
        print("🔍 AI analyzing Apigee configuration...")
        analysis = await self.analyze_apigee_proxy(apigee_files)
        
        # Phase 3: Generate Kong Config
        print("⚙️  AI generating Kong configuration with bundling...")
        kong_config_yaml = await self.generate_kong_config(analysis, apigee_files)
        
        # Phase 4: Generate Custom Plugins
        print("🔌 AI generating custom Lua plugins...")
        custom_plugins = await self.generate_custom_plugins(analysis, apigee_files)
        
        # Phase 5: Validate
        print("✅ AI validating configuration...")
        validation = await self.validate_configuration(kong_config_yaml, analysis)
        
        # Phase 6: Calculate Coverage
        print("📊 Calculating migration coverage...")
        coverage = await self.calculate_coverage(analysis, kong_config_yaml)
        
        # Phase 7: Generate Manual Steps
        print("📝 Generating manual migration steps...")
        manual_steps = await self.generate_manual_steps(analysis, coverage, custom_plugins)
        
        # Phase 8: Generate Report
        print("📄 AI generating migration report...")
        migration_report = await self.generate_migration_report(
            analysis, coverage, validation, manual_steps
        )
        
        # Phase 9: Generate Tests
        print("🧪 AI generating test scripts...")
        test_scripts = await self.generate_test_scripts(analysis, kong_config_yaml)
        
        # Parse YAML to dict
        kong_config_dict = yaml.safe_load(kong_config_yaml)
        
        print("✨ Migration package complete!")
        
        return MigrationPackage(
            kong_config=kong_config_dict,
            custom_plugins=custom_plugins,
            coverage=coverage,
            manual_steps=manual_steps,
            validation=validation,
            migration_report=migration_report,
            test_scripts=test_scripts
        )
    
    # Helper methods
    def _get_language(self, filename: str) -> str:
        """Get language for syntax highlighting"""
        ext = Path(filename).suffix
        mapping = {'.js': 'javascript', '.java': 'java', '.py': 'python'}
        return mapping.get(ext, 'text')
    
    def _extract_yaml(self, content: str) -> str:
        """Extract YAML from AI response"""
        # Remove markdown code blocks
        content = re.sub(r'```ya?ml\n', '', content)
        content = re.sub(r'```\n?', '', content)
        return content.strip()
    
    def _extract_json(self, content: str) -> dict:
        """Extract JSON from AI response"""
        # Try to find JSON in content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Try to parse entire content
        try:
            return json.loads(content)
        except:
            return {}
    
    def _generate_plugin_name(self, filename: str) -> str:
        """Generate plugin name from filename"""
        name = Path(filename).stem
        name = re.sub(r'[^a-z0-9]+', '-', name.lower())
        return f"custom-{name}"


# ============================================
# Flask API
# ============================================

app = Flask(__name__)
CORS(app)

generator = AIKongGenerator()


@app.route('/api/ai-generate-migration', methods=['POST'])
async def ai_generate_migration():
    """
    AI-powered complete migration generation
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        # Save temporarily
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        file.save(temp_file.name)
        
        # Generate complete migration package
        migration_package = await generator.generate_complete_migration(temp_file.name)
        
        # Clean up
        os.unlink(temp_file.name)
        
        # Convert to JSON-serializable format
        return jsonify({
            'kong_config': migration_package.kong_config,
            'custom_plugins': migration_package.custom_plugins,
            'coverage': migration_package.coverage.dict(),
            'manual_steps': [step.dict() for step in migration_package.manual_steps],
            'validation': migration_package.validation.dict(),
            'migration_report': migration_package.migration_report,
            'test_scripts': migration_package.test_scripts
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/export-complete-package', methods=['POST'])
def export_complete_package():
    """Export complete migration package as ZIP"""
    try:
        data = request.json
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Save Kong config
        with open(f"{temp_dir}/kong-config.yaml", 'w') as f:
            yaml.dump(data['kong_config'], f, default_flow_style=False)
        
        # Save custom plugins
        plugins_dir = f"{temp_dir}/custom-plugins"
        os.makedirs(plugins_dir, exist_ok=True)
        
        for plugin_name, plugin_content in data.get('custom_plugins', {}).items():
            plugin_dir = f"{plugins_dir}/{plugin_name}"
            os.makedirs(plugin_dir, exist_ok=True)
            
            # Parse plugin files
            files = plugin_content.split('=== FILE:')
            for file_section in files[1:]:  # Skip first empty section
                lines = file_section.strip().split('\n', 1)
                if len(lines) == 2:
                    filename = lines[0].strip().replace('===', '').strip()
                    content = lines[1].strip()
                    with open(f"{plugin_dir}/{filename}", 'w') as f:
                        f.write(content)
        
        # Save migration report
        with open(f"{temp_dir}/MIGRATION_REPORT.md", 'w') as f:
            f.write(data['migration_report'])
        
        # Save manual steps
        with open(f"{temp_dir}/MANUAL_STEPS.json", 'w') as f:
            json.dump(data['manual_steps'], f, indent=2)
        
        # Save test scripts
        with open(f"{temp_dir}/test-migration.sh", 'w') as f:
            f.write(data['test_scripts'])
        os.chmod(f"{temp_dir}/test-migration.sh", 0o755)
        
        # Create README
        readme = f"""# Kong Migration Package

## Contents
- `kong-config.yaml` - decK configuration file
- `custom-plugins/` - Custom Lua plugins
- `MIGRATION_REPORT.md` - Comprehensive migration report
- `MANUAL_STEPS.json` - Manual steps required
- `test-migration.sh` - Test scripts

## Quick Start
1. Review MIGRATION_REPORT.md
2. Install custom plugins (see custom-plugins/*/README.md)
3. Validate: `deck validate -s kong-config.yaml`
4. Deploy: `deck sync -s kong-config.yaml`
5. Test: `./test-migration.sh`

## Coverage
- Total Policies: {data['coverage']['total_policies']}
- Auto-migrated: {data['coverage']['auto_migrated']}
- Coverage: {data['coverage']['coverage_percentage']}%
- Bundling Efficiency: {data['coverage']['bundling_efficiency']}%
"""
        with open(f"{temp_dir}/README.md", 'w') as f:
            f.write(readme)
        
        # Create ZIP
        import shutil
        zip_path = f"{temp_dir}.zip"
        shutil.make_archive(temp_dir, 'zip', temp_dir)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name='kong-migration-package.zip',
            mimetype='application/zip'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════╗
║   AI-Driven Kong Configuration Generator                 ║
║   Fully powered by Claude AI                             ║
╚══════════════════════════════════════════════════════════╝

Features:
✓ Intelligent policy bundling
✓ Automatic custom plugin generation
✓ Comprehensive migration coverage
✓ Detailed manual steps
✓ Validation and testing

Starting server...
""")
    app.run(debug=True, port=5000)