
from .utils import read_prompt, format_messages
from services.logging_utils import get_logger
log = get_logger("services.llm_provider")
log.info("Test Scripts module loaded")
import time
import datetime
class TestScripts:
    def __init__(self, llm):
        self.llm = llm
    def build(self, analysis: str, kong_yaml: str) -> str:
        start_time = time.time()
        print("🧪 AI generating test scripts... -- Start", "Time :", start_time)
        tmpl = read_prompt('tests.yaml')
        msgs = format_messages(tmpl['messages'], ANALYSIS=analysis[:2000], KONG_CONFIG=kong_yaml[:2000])
        test_scripts = self.llm.invoke(msgs)
        print("🧪 AI generating test scripts... --End", "--- %s seconds ---" % (time.time() - start_time))
        
        return test_scripts
