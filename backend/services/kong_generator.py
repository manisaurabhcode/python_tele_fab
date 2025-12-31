
from .utils import read_prompt, format_messages
from services.logging_utils import get_logger
import time
import datetime
log = get_logger("services.llm_provider")
log.info("Kong Generator module loaded")
class KongConfigGenerator:
    def __init__(self, llm):
        self.llm = llm
    def generate(self, analysis_text: str) -> str:
        start_time = time.time()
        print("⚙️ AI generating Kong configuration with bundling... -- Start", "Time :", datetime.datetime.now())
        
        log.info("Generating Kong configuration...")
        tmpl = read_prompt('kong_config.yaml')
        log.info(analysis_text)
        messages = format_messages(tmpl['messages'], ANALYSIS=analysis_text)
        log.info(messages)
        kong_config_yaml = self.llm.invoke(messages)
        log.info("Kong configuration generated.")
        log.info(kong_config_yaml)
        print("⚙️ AI generating Kong configuration with bundling...--End", "--- %s seconds ---" % (time.time() - start_time))
        return kong_config_yaml
