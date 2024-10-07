import os
from dotenv import load_dotenv
from django.db import models
from data_provider.services import UpbitDataProvider
from .abstract_trader import AbstractTrader
import uuid
import hashlib
import jwt

# .env 파일 로드
load_dotenv()

class UpbitTrader(AbstractTrader):
    """
     업비트 거래소의 거래 요청을 처리하는 클래스
    """

    RESULT_CHECK_INTERVAL = 10
    ISO_TIMEZONE = "Asia/Seoul"
    AVAILABLE_CURRENCY = {
        "BTC": "KRW-BTC",
        "ETH": "KRW-ETH",
        "DOGE": "KRW-DOGE",
    }

    # 환경 변수에서 API 키 가져오기
    access_key = os.environ.get("UPBIT_OPEN_API_ACCESS_KEY")
    secret_key = os.environ.get("UPBIT_OPEN_API_SECRET_KEY")
    server_url = "https://api.upbit.com/v1/"


    def get_account_info(self):
        """
         내가 보유한 자산 리스트를 보여준다
         Return : {
           "currency": 화폐 단위
           "balance": 주문 가능 금액/수량
           "locked": 주문 중 묶여있는 금액/수량
           "avg_buy_price": 매수평군가
           "avg_buy_price_modified": 매수 평균 가격 수정 여부
           "unit_currency": 평단가 기준 화폐
         }
        """
        jwt_token = self._create_jwt_token()
        authorization = 'Bearer {0}'.format(jwt_token)
        headers = {"Authorization": authorization}

        


    def send_request(self, request_list, callback):
        pass

    def cancel_request(self, request_list, callback):
        pass

    def cancel_all_requests(self):
        pass

    def get_order_info(self, order_id):
        pass

    def get_open_orders(self):
        pass

    def get_closed_orders(self):
        pass

    @staticmethod
    def _create_jwt_token(self, query_string = None):
        payload = {
            "access_key": self.access_key,
            "nonce": str(uuid.uuid4()),
        }
        # 주문 취소의 경우 사용
        if query_string is not None:
            msg = hashlib.sha512()
            msg.update(query_string)
            query_hash = msg.hexdigest()
            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"
        
        return jwt.encode(payload, self.secret_key)




