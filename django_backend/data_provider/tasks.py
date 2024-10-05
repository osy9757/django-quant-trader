from celery import shared_task
from .services import UpbitDataProvider
import logging
import redis
from django.conf import settings

logger = logging.getLogger(__name__)
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

@shared_task(bind=True, max_retries=3)
def fetch_upbit_data(self):
    provider = UpbitDataProvider(currency="BTC", interval=60)
    try:
        logger.info("Starting fetch_upbit_data task")
        provider.get_info()
        logger.info("Completed fetch_upbit_data task")
    except Exception as e:
        logger.error(f"Error fetching data in Celery task: {e}")
        raise self.retry(exc=e, countdown=60)  # 1분 후 재시도

@shared_task(bind=True, max_retries=3)
def fetch_historical_upbit_data(self, start_date=None, max_batch_size=200, api_call_interval=0.5):
    task_id = "fetch_historical_upbit_data"
    if redis_client.get(task_id):
        logger.info(f"Task {task_id} is already running. Skipping this execution.")
        return

    redis_client.set(task_id, "running", ex=3600)  # 1시간 동안 플래그 설정
    provider = UpbitDataProvider(currency="BTC", interval=60)
    try:
        start_date = start_date or settings.UPBIT_START_DATE
        logger.info(f"Starting fetch_historical_upbit_data task from {start_date}")
        provider.fetch_historical_data(start_date=start_date, max_batch_size=max_batch_size, api_call_interval=api_call_interval)
        logger.info("Completed fetch_historical_upbit_data task")
    except Exception as e:
        logger.error(f"Error fetching historical data in Celery task: {e}")
        raise self.retry(exc=e, countdown=300)  # 5분 후 재시도
    finally:
        redis_client.delete(task_id)  # 작업 완료 후 플래그 해제
