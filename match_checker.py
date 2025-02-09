import time
from database import check_pending_results

def start_background_checker():
    """Runs match result checker in the background every 30 minutes."""
    while True:
        check_pending_results()
        time.sleep(1800)  # 30 minutes
