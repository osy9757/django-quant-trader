from celery import shared_task
from data_provider.services import UpbitDataProvider 
import logging
import redis
from django.conf import settings
import requests
import time as t

logger = logging.getLogger(__name__)
redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST, 
    port=settings.REDIS_PORT, 
    db=settings.REDIS_DB
)

LOCK_EXPIRE = 60 * 240  # 240분
LOCK_KEY = "upbit_data_lock"

def acquire_lock():
    return redis_client.setnx(LOCK_KEY, "true")

def release_lock():
    redis_client.delete(LOCK_KEY)

def set_lock_expiry():
    redis_client.expire(LOCK_KEY, LOCK_EXPIRE)

@shared_task(bind=True, max_retries=3)
def fetch_upbit_data(self):
    if not redis_client.exists(LOCK_KEY):  # 락이 걸려있지 않은 경우에만 실행
        provider = UpbitDataProvider(currency="BTC")
        try:
            saved_count, data = provider.get_info()
        except requests.exceptions.RequestException as e:
            logger.error(f"네트워크 오류로 인해 Celery 태스크에서 데이터를 가져오지 못했습니다: {e}\n")
            raise self.retry(exc=e, countdown=10)  # 10초 후 재시도
        except Exception as e:
            logger.error(f"예상치 못한 오류로 인해 Celery 태스크에서 데이터를 가져오지 못했습니다: {e}\n")
            raise self.retry(exc=e, countdown=10)  # 10초 후 재시도
    else:
        logger.info("fetch_upbit_data 태스크가 fetch_missing_upbit_data가 완료되기를 기다리고 있습니다.\n")

@shared_task(bind=True, max_retries=3)
def fetch_missing_upbit_data(self):
    if acquire_lock():
        try:
            set_lock_expiry()
            logger.info("fetch_missing_upbit_data 태스크를 시작합니다...\n")
            provider = UpbitDataProvider(currency="BTC")
            missing_time_groups = provider._get_missing_time_intervals()
            print(f"count missing_time_groups: {len(missing_time_groups)}")
            for missing_time, count in missing_time_groups:
                logger.info(f"{missing_time}에 {count}개의 누락된 데이터를 가져옵니다.\n")
                saved_count, data = provider.get_info(to_time=missing_time, count=count)
                print(f"saved_count: {count}")
                t.sleep(0.5)
            logger.info("fetch_missing_upbit_data 태스크가 완료되었습니다.\n")
        finally:
            release_lock()
    else:
        logger.info("fetch_missing_upbit_data 태스크가 이미 실행 중입니다.\n")
