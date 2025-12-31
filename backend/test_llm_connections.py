
# test_llm_connections.py
import os

from dotenv import load_dotenv

load_dotenv()  

from services.llm_provider import LLMClient, LLMConfig

PROMPT = "In one paragraph, explain what an API Gateway does and list three common features."


def try_provider(provider, model):
    client = LLMClient(LLMConfig(provider=provider, model=model, max_tokens=512, temperature=0.2))
    print(f"\n=== {provider} / {model} ===")
    out = client.invoke([{"role": "user", "content": PROMPT}])
    print((out or "").strip()[:300], "...\n")

if __name__ == "__main__":
    # Quick sanity print to verify critical envs are visible:
    print("AICORE_BASE_URL =", os.getenv("AICORE_BASE_URL"))
    print("CLIENTID        =", "SET" if os.getenv("CLIENTID") else "MISSING")
    print("CLIENTSECRET    =", "SET" if os.getenv("CLIENTSECRET") else "MISSING")

    try_provider("genaihub_langchain", "anthropic--claude-4.5-sonnet")
    try_provider("genaihub_openai", os.getenv("HUB_OPENAI_MODEL", "gpt-4.1"))
    try_provider("genaihub_gemini", "gemini-2.5-flash")


if __name__ == "__main__":
    # --- Gen AI Hub: Anthropic via init_llm (your current setup) -------------
    try_provider("genaihub_langchain", "anthropic--claude-4-sonnet")

    # --- Gen AI Hub: OpenAI (via hub) ---------------------------------------
    # Use a model name that exists in your hub catalog, e.g., "gpt-4.1" or "gpt-5"
    try_provider("genaihub_openai", os.getenv("HUB_OPENAI_MODEL", "gpt-4.1"))

    # --- Gen AI Hub: Gemini 2.5 Flash (via Vertex native) --------------------
    try_provider("genaihub_gemini", "gemini-2.5-flash")

    # --- Azure OpenAI: Chat (LangChain) --------------------------------------
    # Here 'model' can act as deployment fallback; preferred is env AZURE_OPENAI_DEPLOYMENT
    try_provider("azure_openai", os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"))
