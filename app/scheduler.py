import logging

logger = logging.getLogger(__name__)

def start_scheduler() -> None:
    logger.info("Internal APScheduler disabled in v1. Using external cron.")

def stop_scheduler() -> None:
    pass

