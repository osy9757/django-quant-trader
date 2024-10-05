import requests
from .models import UpbitData
import time as t
import pytz
import logging
from django.db.models import F
from django.db.models.functions import TruncMinute
from datetime import datetime, timedelta
from django.conf import settings
import json

class UpbitDataProvider:
    """
    업비트 거래소의 실시간 및 과거 거래 데이터를 제공하는 클래스
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
        self.kst = pytz.timezone('Asia/Seoul')
        self.logger = logging.getLogger(__name__)

    def get_info(self, to_time=None, count=1):
        """지정된 시간대의 데이터를 가져와 저장"""
        try:
            self.query_string["count"] = count
            self.query_string["to"] = to_time
            self.logger.info(f"Requesting data with params: {self.query_string}")

            response = requests.get(self.URL, params=self.query_string)
            response.raise_for_status()
            data = response.json()

            # 데이터가 비어 있거나 예상하지 않은 형식일 경우 처리
            if not data or len(data) == 0:
                raise ValueError("No data received from Upbit API")

            saved_count = 0
            new_data = []
            for candle in data:
                date_time = datetime.strptime(candle["candle_date_time_kst"], "%Y-%m-%dT%H:%M:%S")
                date_time = self.kst.localize(date_time)

                candle_info = {
                    "market": self.query_string["market"],
                    "date_time": date_time,
                    "opening_price": candle["opening_price"],
                    "high_price": candle["high_price"],
                    "low_price": candle["low_price"],
                    "closing_price": candle["trade_price"],
                    "acc_price": candle["candle_acc_trade_price"],
                    "acc_volume": candle["candle_acc_trade_volume"],
                }
                new_data.append(candle_info)
                saved_count += 1

            # Bulk create new data
            UpbitData.objects.bulk_create([UpbitData(**data) for data in new_data])

            self.logger.info(f"Fetched and saved {saved_count} candles")
            return saved_count

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error occurred: {e}")
        except ValueError as e:
            self.logger.error(f"Data processing error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error in get_info: {e}")
        return 0

    def fetch_historical_data(self, start_date=None, max_batch_size=200, api_call_interval=0.5):
        """지정한 날짜부터 현재까지의 데이터 중 빈 시간대의 데이터를 분 단위로 가져와서 저장"""
        start_date = start_date or settings.UPBIT_START_DATE  # 기본값 설정
        current_time = datetime.now(self.kst)  # 현재 시간을 KST로 설정
        start_time = datetime.strptime(start_date,"%Y-%m-%dT%H:%M:%S%z")

        # 데이터베이스에 있는 모든 시간대를 가져옴 (정렬 추가)
        existing_times = list(UpbitData.objects.filter(
            market=self.query_string["market"],
            date_time__gte=start_time,
            date_time__lte=current_time
        ).annotate(
            minute=TruncMinute('date_time')
        ).order_by('minute').values_list('minute', flat=True))  # 'minute'으로 정렬

        existing_times = [datetime.strftime(self.kst.localize(time_str), "%Y-%m-%dT%H:%M:%S%z") for time_str in existing_times]
        existing_times = [time_str[:-2] + ':' + time_str[-2:] for time_str in existing_times]


        # 모든 분 단위 시간대 생성
        total_minutes = int((current_time - start_time).total_seconds() / 60)
        all_times = [start_time + timedelta(minutes=i) for i in range(total_minutes + 1)]

        all_times_iso = []
        for time in all_times:
            to_time_iso = time.strftime('%Y-%m-%dT%H:%M:%S%z')
            to_time_iso = to_time_iso[:-2] + ':' + to_time_iso[-2:]  # ISO 8601 형식으로 ':' 추가
            all_times_iso.append(to_time_iso)

        # 비교 후 missing_times 계산
        missing_times = sorted(set(all_times_iso) - set(existing_times))
        
        # 그룹을 나누어 처리
        split_groups = []
        for i in range(0, len(missing_times), max_batch_size):
            split_group = missing_times[i:i + max_batch_size]
            split_groups.append((split_group[-1], len(split_group)))  # 그룹의 마지막 시간과 그룹의 크기 저장

        total_groups = len(split_groups)

        for i, (end, count) in enumerate(split_groups, 1):
            try:
                to_time = end
                saved_count = self.get_info(to_time=to_time, count=count)
                self.logger.info(f"Group {i}/{total_groups}: Fetched and saved {saved_count} candles")
            except requests.exceptions.RequestException as e:
                if e.response.status_code == 429:
                    self.logger.error(f"Rate limit exceeded: {e}. Retrying after delay.")
                    t.sleep(60)  # 1분 대기 후 재시도
                    saved_count = self.get_info(to_time=to_time, count=count)
                else:
                    self.logger.error(f"Network error occurred: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error in fetch_historical_data for group {i}: {e}")
                t.sleep(10)
            t.sleep(api_call_interval)  # 각 API 호출 사이에 대기 시간 추가

        self.logger.info("Completed fetching historical data for missing time periods")