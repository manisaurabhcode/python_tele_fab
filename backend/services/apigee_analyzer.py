
"""
apigee_analyzer.py (fixed)
- Robust ZIP bundle extraction for Apigee proxies/shared flows
- Safe decoding and size limiting to avoid memory spikes
- Clean prompt formatting for the analyzer LLM stage
"""
from __future__ import annotations
import zipfile
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
import time
from .utils import read_prompt, format_messages
from services.logging_utils import get_logger
log = get_logger("services.llm_provider")
log.info("Apigee Analyzer module loaded")

_TEXT_EXTS = (
    '.xml', '.json', '.properties', '.yml', '.yaml', '.txt', '.md',
    '.js', '.py', '.java', '.ts'
)
_CODE_EXTS = ('.js', '.py', '.java', '.ts')

_MAX_XML_LEN = 2000 * 50   # ~100k chars
_MAX_CODE_LEN = 1500 * 50  # ~75k chars
_MAX_CFG_LEN = 1500 * 30   # ~45k chars

_DEF_ENCODING_ORDER = ['utf-8', 'latin-1']

def _safe_read(zf: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    """Read a member from zip, decode with fallbacks, return text or empty string."""
    try:
        raw = zf.read(member.filename)
    except Exception:
        return ''
    for enc in _DEF_ENCODING_ORDER:
        try:
            return raw.decode(enc, errors='ignore')
        except Exception:
            continue
    try:
        return raw.decode('utf-8', errors='ignore')
    except Exception:
        return ''

def _trim(s: str, max_len: int) -> str:
    if not s:
        return ''
    return s[:max_len]

class BundleExtractor:
    """Extract a combined view of an Apigee bundle from a .zip file."""
    def extract(self, zip_path: str) -> Dict[str, Any]:
        start_time = time.time()
        print("📦 Extracting Apigee proxy bundle... -- Start", "Time :", datetime.datetime.now())
        out: Dict[str, Any] = {
            'proxy_name': Path(zip_path).stem,
            'xml_files': {},
            'code_files': {},
            'config_files': {}
        }
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    name = info.filename
                    lower = name.lower()
                    # Skip obvious binaries
                    if any(lower.endswith(ext) for ext in _TEXT_EXTS):
                        text = _safe_read(z, info)
                        if not text:
                            continue
                        if lower.endswith('.xml'):
                            out['xml_files'][name] = _trim(text, _MAX_XML_LEN)
                        elif lower.endswith(_CODE_EXTS):
                            out['code_files'][name] = _trim(text, _MAX_CODE_LEN)
                        else:
                            out['config_files'][name] = _trim(text, _MAX_CFG_LEN)
        except Exception:
            # Return whatever was collected to avoid hard failure
            return out
        print("📦 Extracting Apigee proxy bundle... --End", "--- %s seconds ---" % (time.time() - start_time))
        return out

class ApigeeAnalyzer:
    """LLM-driven analyzer that summarizes policies, flows, and intent."""
    def __init__(self, llm):
        self.llm = llm

    def _bundle_to_text(self, bundle: Dict[str, Any]) -> str:
        xml_part = "\n\n".join([f"## {k}\n" + v for k, v in (bundle.get('xml_files') or {}).items()]) or 'No XML'
        code_part = "\n\n".join([f"## {k}\n" + v for k, v in (bundle.get('code_files') or {}).items()]) or 'No Code'
        cfg_part = "\n\n".join([f"## {k}\n" + v for k, v in (bundle.get('config_files') or {}).items()]) or ''
        return f"{xml_part}\n\n{code_part}\n\n{cfg_part}".strip()

    def analyze(self, bundle: Dict[str, Any], scoring_rules: Dict[str, int]) -> str:
        # Prepare prompt
        log.info("Analyzing bundle")
        start_time = time.time()
        print("🔍 AI analyzing Apigee configuration... Start", "Time :", datetime.datetime.now())
        rules_text = "\n".join([f"- {k}: {v}" for k, v in (scoring_rules or {}).items()])
        body = self._bundle_to_text(bundle)
        tmpl = read_prompt('analyzer.yaml')
        msgs = format_messages(tmpl['messages'], SCORING_RULES=rules_text, PROXY_CONTENTS=body)
        # Invoke LLM
        log.info("Invoking Apigee Analyzer LLM")
        result = self.llm.invoke(msgs)
        log.info("Apigee Analyzer LLM invocation completed")
        log.debug("Apigee Analyzer LLM result", extra={"result_preview": result[:500]})
        

        # Analyzer prompt requests JSON-only, but some providers may add extra text.
        # Return raw result; downstream can parse/validate JSON as needed.
        print("🔍 AI analyzing Apigee configuration... End", "--- %s seconds ---" % (time.time() - start_time))
        return result
