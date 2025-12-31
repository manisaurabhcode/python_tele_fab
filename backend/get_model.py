
import os
from dotenv import load_dotenv
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client

load_dotenv()
os.environ["AICORE_AUTH_URL"] = os.getenv("URL") + "/oauth/token"
os.environ["AICORE_CLIENT_ID"] = os.getenv("CLIENTID")
os.environ["AICORE_CLIENT_SECRET"] = os.getenv("CLIENTSECRET")
os.environ["AICORE_BASE_URL"] = os.getenv("AI_API_URL")
os.environ["AICORE_RESOURCE_GROUP"] = "default"

def main():
    proxy_client = get_proxy_client()  # default hub client

    # Try to list all models via the registry (if available)
    try:
        from gen_ai_hub.proxy.langchain.init_models import ModelCatalog
        catalog = ModelCatalog()
        registry = getattr(catalog, "registry", None)
        if registry and isinstance(registry, dict):
            print("=== All LLM model keys in your Gen AI Hub catalog ===")
            for key in sorted(registry.keys()):
                print("-", key)
            return
        else:
            print("ModelCatalog found, but no registry attribute. Falling back to probing common models.")
    except Exception as e:
        print("[Info] ModelCatalog not available or failed:", e)

    # Fallback: probe common model names
    try:
        from gen_ai_hub.proxy.langchain.init_models import init_llm
        candidate_llms = [
            "anthropic--claude-4-sonnet",
            "gpt-5",
            "gpt-4",
            "gemini-2.5-flash",
        ]
        print("\n=== Probing catalog via init_llm(...) ===")
        for name in candidate_llms:
            try:
                _ = init_llm(name, max_tokens=1)
                print("[AVAILABLE]", name)
            except Exception as ex:
                print("[MISSING]  ", name, "-", str(ex).split("\n")[0])
    except Exception as e:
        print("[Info] init_llm probe not available:", e)

if __name__ == "__main__":
    main()
