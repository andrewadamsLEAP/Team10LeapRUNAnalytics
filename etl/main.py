from apscheduler.schedulers.blocking import BlockingScheduler
from pipeline import run
import os
from dotenv import load_dotenv

load_dotenv()

def safe_run():
    try:
        run()
    except Exception:
        print("ETL run failed; watermark was not advanced")


if __name__ == "__main__":
    print("Starting trade warehouse ETL every %d seconds" % int(os.getenv("ETL_INTERVAL_SECONDS")))
    safe_run()
    scheduler = BlockingScheduler()
    scheduler.add_job(safe_run, "interval", seconds=int(os.getenv("ETL_INTERVAL_SECONDS")), max_instances=1, coalesce=True)
    scheduler.start()