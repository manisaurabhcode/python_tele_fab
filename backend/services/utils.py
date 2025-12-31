
import yaml
from pathlib import Path
from typing import Dict, Any, List
import time
from services.logging_utils import get_logger
log = get_logger("services.llm_provider")
log.info("Utils module loaded")

PROMPTS_DIR = Path(__file__).resolve().parents[1] / 'prompts'
CONFIG_DIR = Path(__file__).resolve().parents[1] / 'config'

def load_settings() -> Dict[str, Any]:
    path = CONFIG_DIR / 'settings.yaml'
    return yaml.safe_load(path.read_text(encoding='utf-8'))

def read_prompt(name: str) -> Dict[str, Any]:
    import yaml as _yaml
    p = PROMPTS_DIR / name
    data = _yaml.safe_load(p.read_text(encoding='utf-8'))
    msgs = []
    for m in data.get('messages', []):
        msgs.append({'role': m.get('role','user'), 'content': m.get('content','')})
    return {'messages': msgs}

def format_messages(template_msgs: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
    out = []
    for m in template_msgs:
        content = m['content'].format(**kwargs)
        out.append({'role': m['role'], 'content': content})
    return out
