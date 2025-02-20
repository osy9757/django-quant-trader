# django_backend/strategy/strategy.py
from abc import ABC, abstractmethod

class Strategy(ABC):
    """
     데이터를 통해 매매 판단을 하는 클래스
    """

    @abstractmethod
    def initialize(self,budget, min_price = 5000):
        """
         예산과 최저 매매 가격을 설정합니다.
        """
    
    @abstractmethod
    def get_request(self):
        """
         매매 요청을 반환합니다.
        """

    @abstractmethod
    def update_trade_info(self, info):
        """
         매매 정보를 업데이트합니다.
        """

