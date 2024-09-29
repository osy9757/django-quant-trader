import requests
from .models import UpbitData
from datetime import datetime
import pytz

class UpbitDataProvider:
    """
    업비트 거래소의 실시간 거래 데이터를 제공하는 클래스
    """

    URL = "https://api.upbit.com/v1/candles/minutes/1"
    AVAILABLE_CURRENCY = {
        "BTC": "KRW-BTC",
        "ETH": "KRW-ETH",
        "DOGE": "KRW-DOGE",
    }

    def __init__(self, currency="BTC", interval=60):
        if currency not in self.AVAILABLE_CURRENCY:
            raise ValueError(f"Unsupported currency: {currency}")
        self.query_string = {"market": self.AVAILABLE_CURRENCY[currency], "count": 1}
        self.interval = interval


    def get_info(self):
        """업비트 API에서 데이터를 가져와 저장"""
        response = requests.get(self.URL, params=self.query_string)
        try:
            response.raise_for_status()
            data = response.json()

            # 데이터가 비어 있거나 예상하지 않은 형식일 경우 처리
            if not data or len(data) == 0:
                raise ValueError("No data received from Upbit API")

            # 데이터가 있는 경우 계속 처리
            kst = pytz.timezone('Asia/Seoul')
            date_time = datetime.strptime(data[0]["candle_date_time_kst"], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=kst)

            candle_info = {
                "market": self.query_string["market"],
                "date_time": date_time,
                "opening_price": data[0]["opening_price"],
                "high_price": data[0]["high_price"],
                "low_price": data[0]["low_price"],
                "closing_price": data[0]["trade_price"],
                "acc_price": data[0]["candle_acc_trade_price"],
                "acc_volume": data[0]["candle_acc_trade_volume"],
            }

            # 데이터베이스에 저장
            UpbitData.objects.update_or_create(
                period=self.interval,
                market=candle_info["market"],
                date_time=candle_info["date_time"],
                defaults=candle_info,
            )
            
            print("Data fetched and saved successfully")
            return None  # 반환 값이 필요 없으므로 None 처리
        
        except Exception as e:
            # 에러 발생 시 오류 메시지 출력
            print(f"Failed to fetch or process data from Upbit API: {e}")
            return None

