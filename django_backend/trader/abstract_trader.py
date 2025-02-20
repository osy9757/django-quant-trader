# django_backend/trader/abstract_trader.py
from abc import ABC, abstractmethod

class AbstractTrader(ABC):
    """
    거래 요청을 처리하는 추상 클래스
    """

    @abstractmethod
    def send_request(self, request_list, callback):
        pass

    @abstractmethod
    def cancel_request(self, request_list, callback):
        pass

    @abstractmethod
    def cancel_all_requests(self):
        pass

    @abstractmethod
    def get_account_info(self):
        pass

    @abstractmethod
    def get_order_info(self, order_id):
        pass

    @abstractmethod
    def get_open_orders(self):
        pass

    @abstractmethod
    def get_closed_orders(self):
        pass
