from celery import shared_task
from .services import UpbitDataProvider

@shared_task
def fetch_upbit_data():
    provider = UpbitDataProvider(currency="BTC", interval=60)
    try:
        print("Starting fetch_upbit_data task")
        provider.get_info()
        print("Completed fetch_upbit_data task")
    except Exception as e:
        # Celery 로그에 에러 메시지를 남김
        print(f"Error fetching data in Celery task: {e}")
    return None
