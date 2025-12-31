
"""
llm_provider.py (extended)
Adds:
- genaihub_openai   -> via gen_ai_hub.proxy.langchain.openai.ChatOpenAI
- genaihub_gemini   -> via gen_ai_hub.proxy.native.google_vertexai.GenerativeModel
- azure_openai      -> via langchain_openai.AzureChatOpenAI
Keeps:
- genaihub_langchain (default, e.g., anthropic--claude-4.5-sonnet)
- anthropic_bedrock (optional)
"""

from __future__ import annotations
import os, json
from dataclasses import dataclass
from typing import List, Dict, Any

from services.logging_utils import get_logger
log = get_logger("services.llm_provider")

# ---- Optional adapters (import-guarded) --------------------------------------
try:
    # LangChain style init used for Anthropic via Gen AI Hub (your current default)
    from gen_ai_hub.proxy.langchain.init_models import init_llm
except Exception:
    init_llm = None

try:
    # Gen AI Hub • VertexAI native client for Gemini
    from gen_ai_hub.proxy.native.google_vertexai.clients import GenerativeModel
    from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
except Exception:
    GenerativeModel = None
    get_proxy_client = None

try:
    # Gen AI Hub • OpenAI via LangChain-compatible wrapper
    from gen_ai_hub.proxy.langchain.openai import ChatOpenAI as HubChatOpenAI
except Exception:
    HubChatOpenAI = None

try:
    # Azure OpenAI (LangChain)
    from langchain_openai import AzureChatOpenAI
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
except Exception:
    AzureChatOpenAI = None
    StrOutputParser = None
    ChatPromptTemplate = None

# -----------------------------------------------------------------------------
@dataclass
class LLMConfig:
    provider: str
    model: str
    max_tokens: int = 4000
    temperature: float = 0.2
    top_p: float = 0.9

class LLMClient:
    """
    Unified LLM client supporting:
    - genaihub_langchain  : init_llm(model=...)
    - genaihub_openai     : HubChatOpenAI(proxy_model_name=..., proxy_client=...)
    - genaihub_gemini     : GenerativeModel(...), model_name='gemini-2.5-flash'
    - azure_openai        : AzureChatOpenAI(deployment_name=...)
    - anthropic_bedrock   : (optional; left untouched)
    """

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        # SAP AI Core envs (used by Gen AI Hub)
        if os.getenv('CLIENTID') and os.getenv('AI_API_URL'):
            os.environ["AICORE_AUTH_URL"]     = os.getenv("URL", "") + "/oauth/token"
            os.environ["AICORE_CLIENT_ID"]    = os.getenv("CLIENTID", "")
            os.environ["AICORE_CLIENT_SECRET"]= os.getenv("CLIENTSECRET", "")
            os.environ["AICORE_BASE_URL"]     = os.getenv("AI_API_URL", "")
            os.environ["AICORE_RESOURCE_GROUP"]= os.getenv("AICORE_RESOURCE_GROUP", "default")

    @staticmethod
    def from_env_or_file(settings: Dict[str, Any]) -> 'LLMClient':
        llm_settings = settings.get('llm', {})
        provider = os.getenv('LLM_PROVIDER', llm_settings.get('provider', 'genaihub_langchain'))
        model    = os.getenv('LLM_MODEL',    llm_settings.get('model',    'anthropic--claude-4.5-sonnet'))
        try:
            max_tokens = int(os.getenv('MAX_TOKENS', llm_settings.get('max_tokens', 8000)))
        except Exception:
            max_tokens = llm_settings.get('max_tokens', 8000)
        try:
            temperature = float(os.getenv('TEMPERATURE', llm_settings.get('temperature', 0.2)))
        except Exception:
            temperature = llm_settings.get('temperature', 0.2)

        log.info(f"LLM Config -> Provider: {provider}, Model: {model}, Max Tokens: {max_tokens}, Temperature: {temperature}")
        return LLMClient(LLMConfig(provider=provider, model=model, max_tokens=max_tokens, temperature=temperature))

    # ----------------------- Public API ---------------------------------------
    def invoke(self, messages: List[Dict[str, Any]] | str) -> str:
        msgs = self._normalize_messages(messages)
        p = self.cfg.provider

        if p == 'genaihub_langchain':
            return self._invoke_genaihub_langchain(msgs)

        if p == 'genaihub_openai':
            return self._invoke_genaihub_openai(msgs)

        if p == 'genaihub_gemini':
            return self._invoke_genaihub_gemini(msgs)

        if p == 'azure_openai':
            return self._invoke_azure_openai(msgs)

        if p == 'anthropic_bedrock':
            # optional: if you had Bedrock code earlier, keep or remove as needed
            raise RuntimeError("anthropic_bedrock not configured in this build")

        raise RuntimeError(f"Unsupported LLM provider: {p}")

    # ----------------------- Helpers ------------------------------------------
    def _normalize_messages(self, messages: List[Dict[str, Any]] | str) -> List[Dict[str, Any]]:
        if isinstance(messages, str):
            return [{"role": "user", "content": messages}]
        out = []
        for m in messages or []:
            role = m.get("role") or "user"
            content = m.get("content")
            if content is None:
                continue
            out.append({"role": role, "content": str(content)})
        if not out:
            out = [{"role": "user", "content": "Hello"}]
        return out

    # --- Gen AI Hub via init_llm (e.g., anthropic--claude-4.5-sonnet)
    def _invoke_genaihub_langchain(self, messages: List[Dict[str, Any]]) -> str:
        if init_llm is None:
            raise RuntimeError("gen_ai_hub.langchain.init_models not available in environment")
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

        from langchain_core.output_parsers import StrOutputParser
        llm = init_llm(self.cfg.model, max_tokens=self.cfg.max_tokens, temperature=self.cfg.temperature)
        chain = llm | StrOutputParser()
        return chain.invoke(lc_msgs)

    # --- Gen AI Hub • OpenAI via HubChatOpenAI
    def _invoke_genaihub_openai(self, messages: List[Dict[str, Any]]) -> str:
        if HubChatOpenAI is None or get_proxy_client is None:
            raise RuntimeError("Gen AI Hub OpenAI adapter not available")
        proxy_client = get_proxy_client('gen-ai-hub')
        # self.cfg.model can be "gpt-4.1" / "gpt-5" (per your hub catalog)
        llm = HubChatOpenAI(proxy_model_name=self.cfg.model, proxy_client=proxy_client,
                            temperature=self.cfg.temperature, max_tokens=self.cfg.max_tokens)
        # Minimal prompt pass-through
        content = "\n\n".join(m["content"] for m in messages if m.get("content"))
        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("user", "{user_in}")
        ])
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"user_in": content})

    # --- Gen AI Hub • Gemini 2.5 Flash via VertexAI native client
    def _invoke_genaihub_gemini(self, messages: List[Dict[str, Any]]) -> str:
        if GenerativeModel is None or get_proxy_client is None:
            raise RuntimeError("Gen AI Hub Gemini (Vertex) adapter not available")
        proxy_client = get_proxy_client('gen-ai-hub')
        model = GenerativeModel(proxy_client=proxy_client, model_name=self.cfg.model)
        payload = [{
            "role": "user",
            "parts": [{"text": "\n\n".join(m["content"] for m in messages if m.get("content"))}]
        }]
        resp = model.generate_content(payload)
        # Try common fields
        text = getattr(resp, "output_text", None)
        if text:
            return text

        cand = getattr(resp, 'candidates', None)
        if cand and len(cand) > 0:
            candidate = cand[0]
            # If candidate is a dict
            if isinstance(candidate, dict):
                parts = candidate.get('content', {}).get('parts', [])
            else:
                # If candidate is an object, use attribute access
                content = getattr(candidate, 'content', None)
                parts = getattr(content, 'parts', []) if content else []
            # Now extract text
            if parts:
                if isinstance(parts[0], dict):
                    return parts[0].get('text', str(parts[0]))
                elif hasattr(parts[0], 'text'):
                    return parts[0].text
                else:
                    return parts[0]["text"]
        return str(resp)

    # --- Azure OpenAI • Chat via langchain_openai
    def _invoke_azure_openai(self, messages: List[Dict[str, Any]]) -> str:
        if AzureChatOpenAI is None or ChatPromptTemplate is None or StrOutputParser is None:
            raise RuntimeError("Azure OpenAI (langchain_openai) not available")
        # Required Azure envs:
        # AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT
        api_key     = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint    = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment  = os.getenv("AZURE_OPENAI_DEPLOYMENT") or self.cfg.model  # allow model=deployment_name
        if not (api_key and endpoint and deployment):
            raise RuntimeError("Missing Azure OpenAI envs: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT")

        llm = AzureChatOpenAI(
            openai_api_key=api_key,
            azure_endpoint=endpoint,
            azure_deployment=deployment,
            openai_api_version="2024-05-01-preview",
            temperature=self.cfg.temperature,
            max_tokens=self.cfg.max_tokens,
        )
        content = "\n\n".join(m["content"] for m in messages if m.get("content"))
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("user", "{user_in}")
        ])
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"user_in": content})
