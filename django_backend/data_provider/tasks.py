from celery import shared_task
from data_provider.services import UpbitDataProvider 
import logging
import redis
from django.conf import settings
import requests
import time as t
from django.db import IntegrityError

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

            skipped_groups = []  # 건너뛴 그룹을 저장할 리스트

            for missing_time, count in missing_time_groups:
                try:
                    logger.info(f"{missing_time}에 {count}개의 누락된 데이터를 가져옵니다.\n")
                    saved_count, data = provider.get_info(to_time=missing_time, count=count)
                    print(f"saved_count: {count}")
                #except IntegrityError as e:
                #    logger.warning(f"중복된 데이터로 인해 {missing_time}에 대한 데이터를 건너뜁니다: {e}")
                #    skipped_groups.append({"missing_time": missing_time, "count": count})  # 건너뛴 그룹 기록
                except Exception as e:
                    logger.error(f"예상치 못한 오류로 인해 데이터를 가져오지 못했습니다: {e}")
                    raise self.retry(exc=e, countdown=10)  # 10초 후 재시도
                t.sleep(1)

            # 건너뛴 그룹을 JSON 파일로 저장
            if skipped_groups:
                provider._save_to_json('skipped_groups.json', {"skipped_groups": skipped_groups})

            logger.info("fetch_missing_upbit_data 태스크가 완료되었습니다.\n")
        finally:
            release_lock()
    else:
        logger.info("fetch_missing_upbit_data 태스크가 이미 실행 중입니다.\n")
