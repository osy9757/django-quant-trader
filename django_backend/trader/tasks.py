# django_backend/trader/tasks.py
from celery import shared_task
from .services import UpbitTrader

@shared_task
def get_account_info_task():
    """
    계좌 정보를 가져오는 Celery 작업.
    """
    trader = UpbitTrader()
    return trader.get_account_info()

@shared_task
def send_order_task(market, side, price=None, volume=None, ord_type='best', time_in_force='ioc'):
    """
    주문을 전송하는 Celery 작업.
    """
    trader = UpbitTrader()
    return trader.send_request(market, side, price, volume, ord_type, time_in_force)

@shared_task
def cancel_order_task(request_id):
    """
    주문을 취소하는 Celery 작업.
    """
    trader = UpbitTrader()
    return trader.cancel_request(request_id)
