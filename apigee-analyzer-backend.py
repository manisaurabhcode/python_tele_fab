"""
Apigee to Kong Migration Complexity Analyzer
Backend implementation using LangChain and Claude API
"""

import json
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


# Pydantic models for structured output
class PolicyBreakdown(BaseModel):
    category: str = Field(description="Policy category or name")
    count: int = Field(description="Number of occurrences")
    points: int = Field(description="Complexity points assigned")


class KongEquivalent(BaseModel):
    apigeePolicy: str = Field(description="Apigee policy name")
    kongPlugin: str = Field(description="Equivalent Kong plugin")
    effort: str = Field(description="Migration effort: low, medium, or high")


class MigrationAnalysis(BaseModel):
    complexity: str = Field(description="Overall complexity: simple, medium, or complex")
    totalScore: int = Field(description="Total complexity score")
    breakdown: List[PolicyBreakdown] = Field(description="Detailed score breakdown")
    migrationNotes: List[str] = Field(description="Important migration considerations")
    notRequiredForMigration: List[str] = Field(description="Features not needed in Kong")
    kongEquivalents: List[KongEquivalent] = Field(description="Kong plugin mappings")
    estimatedEffort: str = Field(description="Estimated migration effort in days")


@dataclass
class ComplexityRule:
    """Configurable scoring rules for complexity analysis"""
    custom_policy: int = 5
    javascript_callout: int = 10
    python_callout: int = 10
    service_callout: int = 8
    java_callout: int = 15
    oauth_jwt_complex: int = 10
    transformation_policy: int = 8
    message_logging: int = 5
    quota_spike_arrest: int = 3
    assign_message: int = 2
    verify_api_key: int = 2
    cors_policy: int = 1
    cache_policy: int = 4
    extract_variables_regex: int = 6
    conditional_flows_complex: int = 7
    shared_flow_reference: int = 3
    multiple_target_servers: int = 5
    custom_analytics: int = 6


class ApigeeProxyAnalyzer:
    """Analyzes Apigee proxy bundles for Kong migration complexity"""
    
    def __init__(self, api_key: str = None, rules: ComplexityRule = None):
        """
        Initialize the analyzer
        
        Args:
            api_key: Anthropic API key (if None, will use environment variable)
            rules: Custom complexity rules (uses defaults if None)
        """
        self.rules = rules or ComplexityRule()
        self.llm = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            max_tokens=4000
        )
        
        # Parser for structured output
        self.parser = PydanticOutputParser(pydantic_object=MigrationAnalysis)
        
    def extract_proxy_files(self, zip_path: str) -> Dict[str, str]:
        """Extract relevant files from Apigee proxy bundle"""
        extracted_files = {}
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    if file_info.filename.endswith(('.xml', '.js', '.py', '.java', '.json')):
                        content = zip_ref.read(file_info.filename).decode('utf-8', errors='ignore')
                        extracted_files[file_info.filename] = content
        except Exception as e:
            print(f"Error extracting {zip_path}: {e}")
            
        return extracted_files
    
    def parse_proxy_xml(self, xml_content: str) -> Dict[str, Any]:
        """Parse proxy XML to extract policies and configurations"""
        try:
            root = ET.fromstring(xml_content)
            policies = []
            
            # Extract policy references
            for step in root.findall('.//Step'):
                policy_name = step.find('Name')
                if policy_name is not None:
                    policies.append(policy_name.text)
            
            # Extract target servers
            target_servers = [ts.text for ts in root.findall('.//TargetEndpoint/HTTPTargetConnection/URL')]
            
            return {
                'policies': policies,
                'target_servers': target_servers,
                'has_conditional_flows': len(root.findall('.//Condition')) > 5
            }
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return {'policies': [], 'target_servers': [], 'has_conditional_flows': False}
    
    def create_analysis_prompt(self, proxy_files: Dict[str, Dict[str, str]]) -> str:
        """Create comprehensive prompt for Claude analysis"""
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are an expert in API gateway migrations, specializing in Apigee to Kong Gateway migrations.
Your task is to analyze Apigee proxy configurations and determine migration complexity using a point-based system."""),
            ("user", """Analyze the following Apigee proxy/shared flow configurations for Kong migration complexity.

**Scoring Rules:**
- Custom policy: {custom_policy} points each
- JavaScript/Python callout: {javascript_callout} points each
- ServiceCallout policy: {service_callout} points each
- Java callout: {java_callout} points each
- Complex OAuth/JWT flows: {oauth_jwt_complex} points
- Response/Request transformations (XSLT, JSONToXML): {transformation_policy} points
- Message logging with custom variables: {message_logging} points
- Quota/SpikeArrest policies: {quota_spike_arrest} points each
- AssignMessage policy: {assign_message} points each
- VerifyAPIKey: {verify_api_key} points each
- CORS policy: {cors_policy} points
- Cache policies: {cache_policy} points each
- ExtractVariables with regex: {extract_variables_regex} points each
- Conditional flows (>5): {conditional_flows_complex} points
- Shared flow references: {shared_flow_reference} points each
- Multiple target servers (>3): {multiple_target_servers} points
- Custom analytics: {custom_analytics} points

**Complexity Thresholds:**
- Simple: 0-30 points
- Medium: 31-70 points
- Complex: 71+ points

**Proxy Files to Analyze:**
{proxy_contents}

**Kong Migration Considerations:**
- Identify policies that have direct Kong plugin equivalents
- Flag policies that require custom development
- Note features that Kong handles natively (don't need migration)
- Consider data transformation complexity
- Evaluate authentication/authorization complexity

{format_instructions}

Provide a thorough analysis with accurate scoring and practical migration guidance.""")
        ])
        
        # Format proxy contents
        proxy_contents = ""
        for proxy_name, files in proxy_files.items():
            proxy_contents += f"\n## Proxy: {proxy_name}\n"
            for filename, content in files.items():
                preview = content[:800] if len(content) > 800 else content
                proxy_contents += f"\n### File: {filename}\n```\n{preview}\n```\n"
        
        return prompt_template.format_messages(
            custom_policy=self.rules.custom_policy,
            javascript_callout=self.rules.javascript_callout,
            service_callout=self.rules.service_callout,
            java_callout=self.rules.java_callout,
            oauth_jwt_complex=self.rules.oauth_jwt_complex,
            transformation_policy=self.rules.transformation_policy,
            message_logging=self.rules.message_logging,
            quota_spike_arrest=self.rules.quota_spike_arrest,
            assign_message=self.rules.assign_message,
            verify_api_key=self.rules.verify_api_key,
            cors_policy=self.rules.cors_policy,
            cache_policy=self.rules.cache_policy,
            extract_variables_regex=self.rules.extract_variables_regex,
            conditional_flows_complex=self.rules.conditional_flows_complex,
            shared_flow_reference=self.rules.shared_flow_reference,
            multiple_target_servers=self.rules.multiple_target_servers,
            custom_analytics=self.rules.custom_analytics,
            proxy_contents=proxy_contents,
            format_instructions=self.parser.get_format_instructions()
        )
    
    def analyze_proxies(self, zip_files: List[str]) -> MigrationAnalysis:
        """
        Analyze Apigee proxy bundles and return complexity assessment
        
        Args:
            zip_files: List of paths to proxy bundle ZIP files
            
        Returns:
            MigrationAnalysis object with complexity details
        """
        # Extract all proxy files
        all_proxy_files = {}
        for zip_file in zip_files:
            proxy_name = Path(zip_file).stem
            all_proxy_files[proxy_name] = self.extract_proxy_files(zip_file)
        
        # Create prompt
        messages = self.create_analysis_prompt(all_proxy_files)
        
        # Get analysis from Claude
        chain = self.llm | self.parser
        result = chain.invoke(messages)
        
        return result
    
    def generate_migration_report(self, analysis: MigrationAnalysis, output_path: str = None) -> str:
        """Generate a detailed migration report"""
        
        report = f"""
# Apigee to Kong Migration Complexity Report

## Overall Assessment
- **Complexity Level**: {analysis.complexity.upper()}
- **Total Complexity Score**: {analysis.totalScore}
- **Estimated Effort**: {analysis.estimatedEffort}

## Complexity Breakdown
"""
        for item in analysis.breakdown:
            report += f"- {item.category}: {item.count} occurrences ({item.points} points)\n"
        
        report += "\n## Migration Notes\n"
        for note in analysis.migrationNotes:
            report += f"- {note}\n"
        
        if analysis.notRequiredForMigration:
            report += "\n## Not Required for Kong Migration\n"
            for item in analysis.notRequiredForMigration:
                report += f"- {item}\n"
        
        report += "\n## Kong Plugin Equivalents\n"
        for equiv in analysis.kongEquivalents:
            report += f"- **{equiv.apigeePolicy}** → {equiv.kongPlugin} (Effort: {equiv.effort})\n"
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report)
        
        return report


# Flask API endpoint example
from flask import Flask, request, jsonify
from flask_cors import CORS
import tempfile
import os

app = Flask(__name__)
CORS(app)

# Initialize analyzer (configure with your API key)
analyzer = ApigeeProxyAnalyzer(api_key=os.getenv('ANTHROPIC_API_KEY'))


@app.route('/api/analyze', methods=['POST'])
def analyze_migration():
    """API endpoint to analyze Apigee proxies"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        temp_files = []
        
        # Save uploaded files temporarily
        for file in files:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
            file.save(temp_file.name)
            temp_files.append(temp_file.name)
        
        # Analyze proxies
        result = analyzer.analyze_proxies(temp_files)
        
        # Clean up temp files
        for temp_file in temp_files:
            os.unlink(temp_file)
        
        return jsonify(result.dict())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rules', methods=['GET', 'POST'])
def manage_rules():
    """Get or update complexity scoring rules"""
    if request.method == 'GET':
        return jsonify(analyzer.rules.__dict__)
    else:
        # Update rules
        new_rules = ComplexityRule(**request.json)
        analyzer.rules = new_rules
        return jsonify({'status': 'Rules updated successfully'})


if __name__ == '__main__':
    # Example usage
    print("Apigee to Kong Migration Analyzer")
    print("=" * 50)
    
    # You can test with actual proxy files
    # zip_files = ['proxy1.zip', 'proxy2.zip']
    # result = analyzer.analyze_proxies(zip_files)
    # report = analyzer.generate_migration_report(result, 'migration_report.md')
    # print(report)
    
    # Start Flask API
    app.run(debug=True, port=5000)