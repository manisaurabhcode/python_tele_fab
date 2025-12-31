
"""
llm_provider.py (fixed)
Unified LLM adapter with robust message normalization, provider switching, and
clear error reporting. Works with SAP Gen-AI-Hub proxy adapters you already use.
"""

from __future__ import annotations
import os
import time
import datetime
import json
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from services.logging_utils import get_logger
log = get_logger("services.llm_provider")

log.info("LLM Provider module loaded")
# Optional adapters (available in your environment)
try:
    from gen_ai_hub.proxy.langchain.init_models import init_llm  # LangChain style
except Exception:
    init_llm = None

try:
    from gen_ai_hub.proxy.native.amazon.clients import Session as BedrockSession
except Exception:
    BedrockSession = None

try:
    from gen_ai_hub.proxy.native.google_vertexai.clients import GenerativeModel
    from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
except Exception:
    GenerativeModel = None
    get_proxy_client = None

try:
    from gen_ai_hub.proxy.native.openai import chat as openai_chat
except Exception:
    openai_chat = None

@dataclass
class LLMConfig:
    provider: str
    model: str
    max_tokens: int = 4000
    temperature: float = 0.2
    top_p: float = 0.9

class LLMClient:
    """Unified LLM client that supports multiple providers.
    - genaihub_langchain (default; your current Claude via Gen-AI-Hub)
    - anthropic_bedrock
    - google_vertex
    - openai
    """
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        # Optional: set SAP AI Core env if present
        if os.getenv('CLIENTID') and os.getenv('AI_API_URL'):
            os.environ["AICORE_AUTH_URL"] = os.getenv("URL", "") + "/oauth/token"
            os.environ["AICORE_CLIENT_ID"] = os.getenv("CLIENTID", "")
            os.environ["AICORE_CLIENT_SECRET"] = os.getenv("CLIENTSECRET", "")
            os.environ["AICORE_BASE_URL"] = os.getenv("AI_API_URL", "")
            os.environ["AICORE_RESOURCE_GROUP"] = os.getenv("AICORE_RESOURCE_GROUP", "default")

    @staticmethod
    def from_env_or_file(settings: Dict[str, Any]) -> 'LLMClient':
        llm_settings = settings.get('llm', {})
        provider = os.getenv('LLM_PROVIDER', llm_settings.get('provider', 'genaihub_langchain'))
        model = os.getenv('LLM_MODEL', llm_settings.get('model', 'anthropic--claude-4-sonnet'))
        try:
            max_tokens = int(os.getenv('MAX_TOKENS', llm_settings.get('max_tokens', 8000)))
        except Exception:
            max_tokens = llm_settings.get('max_tokens', 8000)
        try:
            temperature = float(os.getenv('TEMPERATURE', llm_settings.get('temperature', 0.2)))
        except Exception:
            temperature = llm_settings.get('temperature', 0.2)
        log.info("LLM Client configuration loaded from environment or settings")
        log.info(f"LLM Config - Provider: {provider}, Model: {model}, Max Tokens: {max_tokens}, Temperature: {temperature}")

        return LLMClient(LLMConfig(provider=provider, model=model, max_tokens=max_tokens, temperature=temperature))

    # ---- Public API ----
    def invoke(self, messages: List[Dict[str, Any]] | str) -> str:
        """Invoke the configured provider with normalized messages.
        Accepts a list of {role, content} dicts or a raw string (converted to user msg).
        """
        normalized = self._normalize_messages(messages)
        p = self.cfg.provider
        if p == 'genaihub_langchain':
            log.info("Invoking Gen-AI-Hub Claude provider")
            return self._invoke_langchain(normalized)
        if p == 'anthropic_bedrock':
            log.info("Invoking Anthropic Bedrock provider")
            return self._invoke_bedrock(normalized)
        if p == 'google_vertex':
            log.info("Invoking Google Vertex provider")
            return self._invoke_vertex(normalized)
        if p == 'openai':
            log.info("Invoking OpenAI provider")
            return self._invoke_openai(normalized)
        raise RuntimeError(f"Unsupported LLM provider: {p}")

    # ---- Internal helpers ----
    def _normalize_messages(self, messages: List[Dict[str, Any]] | str) -> List[Dict[str, Any]]:
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        out: List[Dict[str, Any]] = []
        for m in messages or []:
            role = m.get('role') or 'user'
            content = m.get('content')
            if content is None:
                continue
            out.append({'role': role, 'content': str(content)})
        if not out:
            out = [{'role': 'user', 'content': 'Hello'}]
        return out

    def _invoke_langchain(self, messages: List[Dict[str, Any]]) -> str:
        log.debug("Invoking LangChain model", extra={"model": self.cfg.model, "max_tokens": self.cfg.max_tokens})
        if init_llm is None:
            raise RuntimeError("gen_ai_hub.langchain.init_models not available in environment")
        # Convert to LangChain messages when possible
        try:
            from langchain.schema import SystemMessage, HumanMessage, AIMessage
            lc_msgs = []
            for m in messages:
                if m['role'] == 'system':
                    lc_msgs.append(SystemMessage(content=m['content']))
                elif m['role'] == 'user':
                    lc_msgs.append(HumanMessage(content=m['content']))
                else:
                    lc_msgs.append(AIMessage(content=m['content']))
        except Exception:
            lc_msgs = messages
        # Build pipeline
        from langchain_core.output_parsers import StrOutputParser
        llm = init_llm(self.cfg.model, max_tokens=self.cfg.max_tokens, temperature=self.cfg.temperature)
        chain = llm | StrOutputParser()
        try:
            out = chain.invoke(lc_msgs)
            log.info("LLM invocation OK", extra={"provider": "genaihub_langchain", "chars": len(str(out))})
        except Exception as e:
            log.exception("LLM invocation failed", exc_info=True, extra={"provider": "genaihub_langchain"})
       #     raise RuntimeError(f"LLM invocation error: {str(e)}") from e
        return out

    def _invoke_bedrock(self, messages: List[Dict[str, Any]]) -> str:
        if BedrockSession is None:
            raise RuntimeError("Bedrock client not available")
        client = BedrockSession().client(model_name=self.cfg.model)
        user_text = "\n\n".join([m['content'] for m in messages if m.get('role') in ('system','user')])
        response = client.converse(
            messages=[{"role":"user","content":[{"text": user_text}]}],
            inferenceConfig={"maxTokens": self.cfg.max_tokens, "temperature": self.cfg.temperature, "topP": self.cfg.top_p}
        )
        try:
            return response['output']['message']['content'][0]['text']
        except Exception:
            return json.dumps(response)

    def _invoke_vertex(self, messages: List[Dict[str, Any]]) -> str:
        if GenerativeModel is None or get_proxy_client is None:
            raise RuntimeError("Vertex client not available")
        proxy_client = get_proxy_client('gen-ai-hub')
        model = GenerativeModel(proxy_client=proxy_client, model_name=self.cfg.model)
        payload = [{"role":"user","parts":[{"text": "\n\n".join([m['content'] for m in messages])}]}]
        resp = model.generate_content(payload)
        # Try to extract text field; fall back to string representation
        try:
            # gen-ai-hub often returns an object with 'candidates' or 'output_text'
            text = getattr(resp, 'output_text', None)
            if text:
                return text
            cand = getattr(resp, 'candidates', None)
            if cand and len(cand) > 0:
                parts = cand[0].get('content', {}).get('parts', [])
                if parts and 'text' in parts[0]:
                    return parts[0]['text']
        except Exception:
            pass
        return str(resp)

    def _invoke_openai(self, messages: List[Dict[str, Any]]) -> str:
        if openai_chat is None:
            raise RuntimeError("OpenAI chat adapter not available")
        kwargs = dict(model_name=self.cfg.model, messages=messages)
        response = openai_chat.completions.create(**kwargs)
        # Try to get a clean text response, fallback to JSON
        try:
            # gen-ai-hub openai adapter may shape responses differently; handle common patterns
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                content = getattr(choice, 'message', None)
                if content and isinstance(content, dict):
                    return content.get('content') or json.dumps(response)
            return json.dumps(response)
        except Exception:
            return json.dumps(response)
