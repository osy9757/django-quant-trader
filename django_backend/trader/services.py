import os
from dotenv import load_dotenv
from .abstract_trader import AbstractTrader
import uuid
import hashlib
import jwt
import requests
import logging
from urllib.parse import urlencode, unquote

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

    def __init__(self):
        self.logger = logging.getLogger(__name__)   
        # 환경 변수에서 API 키 가져오기
        self.access_key = os.environ.get("UPBIT_OPEN_API_ACCESS_KEY")
        self.secret_key = os.environ.get("UPBIT_OPEN_API_SECRET_KEY")
        self.server_url = "https://api.upbit.com/v1/"



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

        return self._request_get(self.server_url + "accounts", headers=headers)        


    def send_request(self, market, side, price = None, volume = None, ord_type = 'best', time_in_force = 'ioc'):
        """
            Upbit에 거래 주문 전송

            request:
                - market (필수): 마켓 ID (예: 'KRW-BTC')
                - side (필수): 주문 유형 (매수: 'bid', 매도: 'ask')
                - volume (필수): 주문량 (지정가 주문 또는 시장가 매도 시 필수, 예: '1.0')
                - price (필수): 주문 가격 (지정가 주문 또는 시장가 매수 시 필수, 예: '1000')
                * 시장가 매도 시 price는 'null' 또는 제외
                * 시장가 매수 시 volume은 'null' 또는 제외
                - ord_type (필수): 주문 타입
                - 'limit': 지정가 주문
                - 'price': 시장가 주문 (매수)
                - 'market': 시장가 주문 (매도)
                - 'best': 최유리 지정가 주문 (필수 필드로 'time_in_force' 필요)
                - identifier (선택): 사용자가 직접 지정하는 주문 식별자 (중복 불가, 오류 발생 시 재요청 불가)
                - time_in_force (선택): IOC(즉시 체결 후 취소), FOK(전체 체결 또는 취소) 설정
                * 'ord_type'이 'limit' 또는 'best'일 때만 지원
                * 시장가 주문은 지원하지 않음

            response:
                - uuid: 주문의 고유 ID (String)
                - side: 주문 종류 (매수 또는 매도, String)
                - ord_type: 주문 방식 (지정가, 시장가 등, String)
                - price: 주문 시 화폐 가격 (NumberString)
                - avg_price: 체결된 주문의 평균가 (NumberString)
                - state: 주문 상태 ('done', 'wait', 'cancel', String)
                - market: 마켓 고유 ID (예: 'KRW-BTC', String)
                - created_at: 주문 생성 시간 (String)
                - volume: 사용자가 입력한 주문량 (NumberString)
                - remaining_volume: 남은 주문량 (NumberString)
                - reserved_fee: 예약된 수수료 (NumberString)
                - remaining_fee: 남은 수수료 (NumberString)
                - paid_fee: 사용된 수수료 (NumberString)
                - locked: 거래에 사용 중인 비용 (NumberString)
                - executed_volume: 체결된 주문량 (NumberString)
                - trade_count: 체결된 주문의 개수 (Integer)
        """
        
        self.logger.info(f"ORDER ##### {'BUY' if side == 'bid' else 'SELL'}")

        params = {
            "market": market,
            "side": side,
            "volume": volume,
            "price": price,
            "ord_type": ord_type,
            "time_in_force": time_in_force,
        }

        query_string = unquote(urlencode(params, doseq=True))
        
        jwt_token = self._create_jwt_token(query_string)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorization}

        return self._request_get(self.server_url + "orders", json=params, headers=headers)

    def cancel_request(self, request_id):
        """
            주문 UUID를 통해 해당 주문에 대한 취소 접수
        """
        
        params = {
            "uuid": request_id,
        }

        query_string = unquote(urlencode(params, doseq=True))

        jwt_token = self._create_jwt_token(query_string)
        authorization = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorization}

        return requests.delete(self.server_url + "orders", parmas=params, headers=headers).json()

    def cancel_all_requests(self):
        pass

    def get_order_info(self, order_id):
        pass

    def get_open_orders(self):
        pass

    def get_closed_orders(self):
        pass

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
    
    def _request_get(self, url: str, headers: dict = None, params: dict = None) -> dict:
        """
        HTTP GET 요청을 수행하고 JSON 응답을 반환합니다.

        :param url: 요청할 URL
        :param headers: 요청에 사용할 헤더
        :param params: 요청에 사용할 파라미터
        :return: JSON 응답 데이터 또는 None
        """
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            result = response.json()
        except ValueError as err:
            self.logger.error(f"Invalid data from server: {err}")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(f"HTTP error occurred: {msg}")
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(f"Request exception: {msg}")
            return None

        return result



