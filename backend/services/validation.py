
import json
import time
import datetime
from .utils import read_prompt, format_messages
from services.logging_utils import get_logger
log = get_logger("services.llm_provider")
log.info("Validation module loaded")
class Validator:
    def __init__(self, llm):
        self.llm = llm
    def validate(self, analysis: str, kong_yaml: str):
        start_time = time.time()
        print("✅ AI validating configuration... -- Start", "Time :", datetime.datetime.now())
        
        tmpl = read_prompt('validation.yaml')
        msgs = format_messages(tmpl['messages'], ANALYSIS=analysis[:3000], KONG_CONFIG=kong_yaml)
        text = self.llm.invoke(msgs)
        try:
            print("✅ AI validating configuration... --End", "--- %s seconds ---" % (time.time() - start_time))
            return json.loads(text)
        except Exception:
            return {"is_valid": False, "errors": ["Validator returned non-JSON"], "warnings": [], "suggestions": []}
