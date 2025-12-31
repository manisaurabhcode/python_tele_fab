
from .utils import read_prompt, format_messages
from services.logging_utils import get_logger
import time
import datetime
log = get_logger("services.llm_provider")
log.info("Report module loaded")

class Report:
    def __init__(self, llm):
        self.llm = llm
    def build(self, analysis: str, stats: dict) -> str:
        start_time = time.time()
        print("📝 Generating manual migration steps... -- Start", "Time :", datetime.datetime.now())
        
        tmpl = read_prompt('report.yaml')
        log.info("Building report with stats:")
        msgs = format_messages(
            tmpl['messages'],
            TOTAL=stats.get('total',0),
            AUTO=stats.get('auto',0),
            COVERAGE_PCT=stats.get('coverage_pct',0),
            BUNDLED=stats.get('bundled',0),
            CUSTOM=stats.get('custom',0),
            EFFICIENCY=stats.get('efficiency',0),
            DATE=datetime.datetime.now().strftime('%Y-%m-%d'),
            ANALYSIS=analysis[:2000])
        log.info("Report messages prepared.")
        log.info(msgs)
        report = self.llm.invoke(msgs)
        print("📝 Generating manual migration steps... --End", "--- %s seconds ---" % (time.time() - start_time))
        return report
