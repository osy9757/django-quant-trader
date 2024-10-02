import requests
from .models import UpbitData
import time
import pytz
import logging
from django.db.models import F
from django.db.models.functions import TruncMinute
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            if to_time:
                self.query_string["to"] = to_time.strftime('%Y-%m-%dT%H:%M:%S')
            self.query_string["count"] = count

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

                # 데이터베이스에 이미 존재하는지 확인
                if UpbitData.objects.filter(market=self.query_string["market"], date_time=date_time).exists():
                    continue

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

    def fetch_historical_data(self, start_date="2019-10-01", max_batch_size=200, api_call_interval=1):
        """지정한 날짜부터 현재까지의 데이터 중 빈 시간대의 데이터를 분 단위로 가져와서 저장"""
        current_time = time.time()
        start_time = time.mktime(time.strptime(start_date, "%Y-%m-%d"))

        # 데이터베이스에 있는 모든 시간대를 가져옴
        existing_times = set(UpbitData.objects.filter(
            market=self.query_string["market"],
            date_time__gte=datetime.fromtimestamp(start_time, self.kst),
            date_time__lte=datetime.fromtimestamp(current_time, self.kst)
        ).annotate(
            minute=TruncMinute('date_time')
        ).values_list('minute', flat=True))

        # 모든 분 단위 시간대 생성
        all_times = set(start_time + 60 * i for i in range(int((current_time - start_time) / 60) + 1))

        # 빈 시간대 계산
        missing_times = sorted(all_times - existing_times, reverse=True)  # 최신 데이터부터 처리

        # 연속된 빈 시간대를 그룹화
        grouped_missing_times = []
        if missing_times:
            group = [missing_times[0]]
            for t in missing_times[1:]:
                if group[-1] - t == 60:  # 1분 간격인 경우에만 같은 그룹
                    group.append(t)
                else:
                    grouped_missing_times.append((group[-1], len(group)))  # 그룹의 마지막 시간과 그룹의 크기 저장
                    group = [t]
            
            # 마지막 그룹 처리
            grouped_missing_times.append((group[-1], len(group)))

        total_groups = len(grouped_missing_times)

        def fetch_and_save_data(end, count, i):
            try:
                to_time = datetime.fromtimestamp(end, self.kst)
                saved_count = self.get_info(to_time=to_time, count=count)
                self.logger.info(f"Group {i}/{total_groups}: Fetched and saved {saved_count} candles")
                return saved_count

            except Exception as e:
                self.logger.error(f"Unexpected error in fetch_historical_data for group {i}: {e}")
                time.sleep(10)
            return 0

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(fetch_and_save_data, end, count, i) for i, (end, count) in enumerate(grouped_missing_times, 1)]
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    self.logger.error(f"Error occurred during parallel execution: {e}")

        self.logger.info("Completed fetching historical data for missing time periods")