
import json
from .utils import read_prompt, format_messages
from services.logging_utils import get_logger
import time
import datetime
import re
from typing import Dict, Any, List
log = get_logger("services.llm_provider")
log.info("Coverage module loaded")

def _safe_json_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        # Try to extract the largest JSON object
        blocks = list(re.finditer(r"\{[\s\S]*\}", text or ""))
        blocks.sort(key=lambda m: len(m.group(0)), reverse=True)
        for m in blocks:
            try:
                return json.loads(m.group(0))
            except Exception:
                continue
    return {}


class Coverage:
    def __init__(self, llm):
        self.llm = llm
    
    def _extract_policies(self, analysis_json: Dict[str, Any]) -> List[Dict[str, str]]:
        policies = []
        for p in (analysis_json.get("policies_analysis") or []):
            name = p.get("policy_name") or ""
            ptype = p.get("policy_type") or ""
            if name:
                policies.append({"name": name, "type": ptype})
        log.info(f"Extracted {len(policies)} policies from analysis.")
        log.info(policies)
        return policies

    def compute(self, analysis_text: str, kong_yaml_text: str) -> Dict[str, Any]:
        # Parse analysis JSON
        start_time = time.time()
        print("📈 Calculating migration coverage... -- Start", "Time :", datetime.datetime.now())
        
        analysis_json = _safe_json_loads(analysis_text or "")
        policies = self._extract_policies(analysis_json)
        policy_count = len(policies)
        log.info(f"Detected {policy_count} policies in analysis.")
        policy_list_lines = [
            f"- {p['name']}" + (f" ({p['type']})" if p.get("type") else "")
            for p in policies
        ]
        policy_list = "\n".join(policy_list_lines) or "- (none detected)"

        # Prepare prompt
        tmpl = read_prompt('coverage.yaml')
        msgs = format_messages(
            tmpl['messages'],
            ANALYSIS=(analysis_text or "")[:8000],
            KONG_CONFIG=(kong_yaml_text or "")[:8000],
            POLICY_LIST=policy_list,
            POLICY_COUNT=policy_count
        )
        log.info("Prepared coverage prompt messages.")
        log.info(msgs)

        # Invoke LLM
        text = self.llm.invoke(msgs)
        result = _safe_json_loads(text)
        log.info("Coverage result:")
        log.info(result)

        # Fallbacks: fill minimal fields if missing/zeros
        result = result if isinstance(result, dict) else {}
        result.setdefault("total_policies", policy_count)
        # if coverage_percentage missing, compute naive percentage from policy_mappings length
        if "coverage_percentage" not in result or not isinstance(result["coverage_percentage"], (int, float)):
            mapped = len([m for m in result.get("policy_mappings", []) if m.get("kong_solution")]) if isinstance(result.get("policy_mappings"), list) else 0
            result["coverage_percentage"] = round(100 * (mapped / result["total_policies"])) if result["total_policies"] else 0

        # Ensure bundling_analysis keys exist
        ba = result.get("bundling_analysis") or {}
        ba.setdefault("total_bundles", 0)
        ba.setdefault("bundled_policies_count", 0)
        ba.setdefault("efficiency_gain", "0%")
        result["bundling_analysis"] = ba
        print("📈 Calculating migration coverage... --End", "--- %s seconds ---" % (time.time() - start_time))
        # Ensure arrays exist
        for key in ("policy_mappings", "not_required_policies"):
            if key not in result or not isinstance(result[key], list):
                result[key] = []

        return result

 