
"""
plugin_builder.py (hardened)
- Distills Apigee callout behavior into a strict JSON SPEC using the LLM
- Generates Kong Lua plugin files (handler.lua, schema.lua, README.md)
- Robust JSON extraction, safe prompt formatting, defensive file splitting
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Any, Union

from .utils import read_prompt
from services.logging_utils import get_logger

log = get_logger("services.plugin_builder")

# Prompt/input caps (keep calls fast / under upstream proxy limits)
_MAX_ANALYSIS = 3000
_MAX_CODE     = 8000

# Section splitting markers and helpers
_FILE_SPLIT_PATTERN = re.compile(r"^\s*===\s*FILE:\s*(.*?)\s*===\s*$", re.MULTILINE)
_CODE_FENCE         = re.compile(r"^\s*```+([a-zA-Z0-9_-]*)\s*$|^\s*```+\s*$", re.MULTILINE)

# Extract JSON objects (fallback to the largest one)
_JSON_BLOCKS        = re.compile(r"\{[\s\S]*\}")

_LANG_BY_EXT = {
    '.js': 'javascript',
    '.py': 'python',
    '.java': 'java',
    '.ts': 'typescript'
}
_REQUIRED_KEYS = ["plugin_name", "summary", "entry_points", "config"]


# ---------- Safe formatting (avoid KeyError from literal braces in prompts) ----------
class _SafeDict(dict):
    def __missing__(self, key):
        # Leave unknown placeholders intact as literal text
        return "{" + key + "}"


def _safe_format_messages(template_msgs, **kwargs):
    msgs = []
    for m in template_msgs or []:
        content = m.get('content', '')
        role    = m.get('role', 'user')
        try:
            content = content.format_map(_SafeDict(**kwargs))
        except Exception:
            # Pass through unformatted content on any formatting error
            pass
        msgs.append({"role": role, "content": content})
    return msgs


# ---------- Sanitization & parsing helpers ----------
def _sanitize_code_snippet(s: Union[str, bytes, None], limit: int = _MAX_CODE) -> str:
    if s is None:
        return ""
    if isinstance(s, bytes):
        try:
            s = s.decode("utf-8", errors="ignore")
        except Exception:
            s = s.decode("latin-1", errors="ignore")
    s = str(s)
    # Strip code fences and normalize line endings
    s = _CODE_FENCE.sub("", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s[:limit]


def _safe_json_loads(text: str) -> Dict[str, Any]:
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    # Fallback: pick the largest JSON block (often the real SPEC)
    blocks = list(_JSON_BLOCKS.finditer(text or ""))
    blocks.sort(key=lambda m: len(m.group(0)), reverse=True)
    for m in blocks:
        try:
            return json.loads(m.group(0))
        except Exception:
            continue
    return {}


def _ensure_spec(spec: Dict[str, Any], filename: str) -> Dict[str, Any]:
    # Add required keys and defaults
    for k in _REQUIRED_KEYS:
        if k not in spec:
            spec[k] = {} if k == "config" else "unknown" if k == "summary" else []
    if not spec.get("plugin_name"):
        spec["plugin_name"] = f"custom_{Path(filename).stem}" if filename else "custom_plugin"
    return spec


def _schema_from_spec(spec: Dict[str, Any]) -> str:
    """Build a minimal, valid Kong schema from SPEC.config."""
    cfg_fields = []
    for k, v in (spec.get("config") or {}).items():
        typ = "string"
        if isinstance(v, bool): typ = "boolean"
        elif isinstance(v, (int, float)): typ = "number"
        cfg_fields.append({k: {"type": typ}})
    return (
        'return { name = "' + (spec.get("plugin_name","custom-plugin")) + '", '
        'fields = { { config = { type = "record", fields = ' + json.dumps(cfg_fields) + ' } } } }'
    )


def _split_sections(s: str) -> Dict[str, str]:
    """Split LLM output by === FILE: ... === markers; heuristic fallback when missing."""
    if not s:
        return {}
    s = _CODE_FENCE.sub("", s)

    matches = list(_FILE_SPLIT_PATTERN.finditer(s))
    if matches:
        files = {}
        for i, m in enumerate(matches):
            fname = m.group(1).strip()
            start = m.end()
            end   = matches[i+1].start() if i+1 < len(matches) else len(s)
            body  = s[start:end].strip()
            files[fname] = body
        return files

    # Heuristic: split by schema.lua mention if markers missing
    parts = re.split(r'(?i)\bschema\.lua\b', s)
    if len(parts) >= 2:
        return {"handler.lua": parts[0].strip(), "schema.lua": parts[1].strip()}

    return {"handler.lua": s.strip()}


# ---------- Main class ----------
class PluginBuilder:
    def __init__(self, llm):
        self.llm = llm

    def distill_spec(self, filename: str, lang: str, analysis: Union[str, None], code_chunk: Union[str, bytes, None]) -> Dict[str, Any]:
        """
        Derive SPEC JSON describing plugin behavior from callout code + analysis.

        - Accepts str/bytes/None for `code_chunk` (decodes and sanitizes).
        - Uses SafeDict for prompt formatting to avoid KeyError on literal braces.
        - Parses the largest JSON object if multiple appear in the LLM output.
        - Returns a safe fallback SPEC if parsing fails.
        """
        # Infer language if unknown
        ext  = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        lang = lang if lang and lang != "unknown" else _LANG_BY_EXT.get(ext, "unknown")

        sanitized_code   = _sanitize_code_snippet(code_chunk, _MAX_CODE)
        trimmed_analysis = (analysis or "")[:_MAX_ANALYSIS]

        tmpl = read_prompt("plugin_analysis.yaml")
        msgs = _safe_format_messages(
            tmpl.get("messages", []),
            FILENAME=filename,
            LANG=lang,
            ANALYSIS=trimmed_analysis,
            CODE=sanitized_code
        )

        try:
            text = self.llm.invoke(msgs)
        except Exception as e:
            # Return minimal fallback on LLM error (keeps pipeline moving)
            log.warning("LLM invocation failed in distill_spec", extra={"source_filename": filename, "error": str(e)})
            return _ensure_spec({
                'plugin_name': f"custom_{Path(filename).stem}" if filename else 'custom_plugin',
                'summary': f'LLM invocation failed: {e.__class__.__name__}',
                'entry_points': ['access', 'response'],
                'io': {'request': {}, 'response': {}},
                'flows': [],
                'errors': [],
                'config': {},
                'logging': {'level': 'info'},
                'dependencies': [],
                'compat_notes': []
            }, filename)

        spec = _safe_json_loads(text)
        if not spec or not isinstance(spec, dict):
            log.warning("SPEC JSON empty or invalid; applying fallback", extra={"source_filename": filename})
            spec = {
                'plugin_name': f"custom_{Path(filename).stem}" if filename else 'custom_plugin',
                'summary': 'Behavior extracted from Apigee callout',
                'entry_points': ['access', 'response'],
                'io': {'request': {}, 'response': {}},
                'flows': [],
                'errors': [],
                'config': {},
                'logging': {'level': 'info'},
                'dependencies': [],
                'compat_notes': []
            }

        spec = _ensure_spec(spec, filename)
        log.debug("SPEC parsed", extra={"plugin_name": spec.get("plugin_name")})
        return spec

    def generate_files(self, spec: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate handler.lua, schema.lua, README.md from SPEC.
        """
        tmpl = read_prompt('plugin_generation.yaml')
        spec_json = json.dumps(spec, ensure_ascii=False)
        msgs = _safe_format_messages(tmpl.get('messages', []), SPEC_JSON=spec_json)

        try:
            out = self.llm.invoke(msgs)
        except Exception as e:
            log.warning("LLM invocation failed in generate_files; returning fallbacks", extra={"plugin_name": spec.get("plugin_name"), "error": str(e)})
            out = ""

        files = _split_sections(out)

        # Fallbacks to ensure a complete plugin
        if not files.get('handler.lua'):
            files['handler.lua'] = (
                '-- handler placeholder\n'
                'local kong = kong\n'
                'local Plugin = { PRIORITY = 1000, VERSION = "1.0.0" }\n'
                'function Plugin:access(conf) kong.log.debug("access phase") end\n'
                'return Plugin'
            )
        if not files.get('schema.lua'):
            files['schema.lua'] = _schema_from_spec(spec)
        if not files.get('README.md'):
            files['README.md'] = f'# {spec.get("plugin_name","Custom Plugin")}\n\nGenerated from Apigee callout.'

        log.info("Plugin files generated", extra={"plugin_name": spec.get("plugin_name"), "file_names": list(files.keys())})
        return files
