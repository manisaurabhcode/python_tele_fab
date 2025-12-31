
# manual_steps.py
import json
from .utils import read_prompt, format_messages
from services.logging_utils import get_logger
import re
from typing import Dict, Any, List, Union
import time
import datetime
import re
from typing import Dict, Any, List
log = get_logger("services.llm_provider")
log.info("Coverage module loaded")

def _to_json_str(data: Union[str, Dict, List]) -> str:
    """Return a JSON string regardless of input type."""
    if isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=False)
    return str(data or "")

def _safe_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        # Extract largest JSON object if the LLM returned text with prose + JSON
        blocks = list(re.finditer(r"\{[\s\S]*\}", text or ""))
        blocks.sort(key=lambda m: len(m.group(0)), reverse=True)
        for m in blocks:
            try:
                return json.loads(m.group(0))
            except Exception:
                continue
        return {}

class ManualSteps:
    def __init__(self, llm):
        self.llm = llm

    def _extract_policies(self, analysis_json: Dict[str, Any]) -> List[Dict[str, str]]:
        policies = []
        for p in (analysis_json.get("policies_analysis") or []):
            name = p.get("policy_name") or ""
            ptype = p.get("policy_type") or ""
            if name:
                policies.append({"name": name, "type": ptype})
        return policies

    def m_steps(self, analysis_text, coverage, custom_plugins) -> List[Dict[str, Any]]:
        # Ensure we have strings
        analysis_text = _to_json_str(analysis_text)
        coverage = _to_json_str(coverage)
        custom_plugins = _to_json_str(custom_plugins)

        start_time = time.time()
        print("📈 Generating Manual Steps... -- Start", "Time :", datetime.datetime.now())

        analysis_json = _safe_json_loads(analysis_text or "")
        policies = self._extract_policies(analysis_json)
        policy_count = len(policies)
        policy_list_lines = [
            f"- {p['name']}" + (f" ({p['type']})" if p.get("type") else "")
            for p in policies
        ]
        policy_list = "\n".join(policy_list_lines) or "- (none detected)"
        log.info(custom_plugins)
        #custom_plugin_list = "\n".join([f"- {name}" for name in custom_plugins]) or "None"
        #custom_plugin_list = "\n".join([f"- {name}" for name in custom_plugins]) or "None"
        
        custom_plugin_list = "\n".join([f"- {name}" for name in custom_plugins.keys()]) or "None"

        #print(custom_plugin_list)
        log.info(f"Policy List:\n{custom_plugin_list}")

        coverage_json = _safe_json_loads(coverage or "")
        log.info(f"Coverage JSON: {coverage_json}")
        #print(coverage)
        total = coverage_json.get('total_policies', 0)
        
        mappings = coverage_json.get('policy_mappings', [])

        total = coverage_json.get('total_policies', 0)
        auto = sum(1 for m in mappings if m.get('auto_generated'))
        #bundled = coverage_json.get('bundling_analysis', {}).get('bundled_policies_count', 0)
        
        custom = sum(1 for m in mappings if m.get('requires_custom_plugin'))

        not_required = len(coverage_json.get('not_required_policies', []))
        


        tmpl = read_prompt('manual_steps.yaml')
        msgs = format_messages(
            tmpl['messages'],
            ANALYSIS=(analysis_text or "")[:8000],
            POLICY_LIST=policy_list,
            TOTAL=total,
            AUTO=auto,
            CUSTOM=custom,
            NOT_REQUIRED=not_required,
            CUSTOM_LIST=custom_plugin_list,
        )

        text = self.llm.invoke(msgs)
        result = _safe_json_loads(text)
        result = result if isinstance(result, dict) else {}
        result.setdefault("total_policies", policy_count)

        steps_data = self._extract_json(result) or []
        return [ManualSteps(**step) for step in steps_data]
