import requests
from data_provider.models import UpbitData  
import time as t
import pytz
import logging
from django.db.models.functions import TruncMinute
from datetime import datetime, timedelta
from django.conf import settings
import json
import os


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

    def __init__(self, currency="BTC"):
        if currency not in self.AVAILABLE_CURRENCY:
            raise ValueError(f"Unsupported currency: {currency}")
        self.query_string = {"market": self.AVAILABLE_CURRENCY[currency], "count": 1}
        self.kst = pytz.timezone('Asia/Seoul')
        self.logger = logging.getLogger(__name__)

    def get_info(self, market="KRW-BTC", to_time=None, count=1):
        """
        업비트 API에서 데이터를 가져와 저장
        """
        data = self.__get_data_from_upbit(market, to_time, count)
        saved_count = self.__save_data_to_db(data, to_time, count)

        if to_time:
            self.logger.info(f"Missing data fetched successfully at {to_time}. {saved_count} records saved\n")
        else:
            self.logger.info(f"Data fetched successfully. {saved_count} records saved\n")
        return saved_count, data

    def __get_data_from_upbit(self, market="KRW-BTC", to_time=None, count=1):
        """
        업비트 API에서 데이터를 가져오는 함수
        """

        self.query_string["market"] = market
        self.query_string["count"] = count
        self.query_string["to"] = to_time

        response = requests.get(self.URL, params=self.query_string)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            raise ValueError("No data received from Upbit API")

        return data
    
    def __save_data_to_db(self, data, to_time, count):
        """
        데이터를 데이터베이스에 저장하는 함수
        """
        new_data = []

        if isinstance(to_time, str):
            to_time = datetime.strptime(to_time, '%Y-%m-%dT%H:%M:%S+09:00')
        to_time = to_time.replace(second=0)
        to_time = self.kst.localize(to_time)

        # to_time에서 count 만큼의 분봉 시간을 요청 시간 리스트로 생성
        requested_times = [to_time - timedelta(minutes=i) for i in range(count)]   

        # 받은 데이터를 시간 순으로 정렬
        data_times = {self.kst.localize(datetime.strptime(candle["candle_date_time_kst"], "%Y-%m-%dT%H:%M:%S")): candle for candle in data}

        for request_time in requested_times:
            # 요청한 시간대와 일치하는 데이터가 있는지 확인
            matching_data = data_times.get(request_time)

            if matching_data:
                # 응답 데이터가 요청 시간과 일치하는 경우
                candle_info = {
                    "market": self.query_string["market"],
                    "date_time": request_time,
                    "opening_price": matching_data["opening_price"],
                    "high_price": matching_data["high_price"],
                    "low_price": matching_data["low_price"],
                    "closing_price": matching_data["trade_price"],
                    "acc_price": matching_data["candle_acc_trade_price"],
                    "acc_volume": matching_data["candle_acc_trade_volume"],
                }
            else:
                # 응답 데이터가 요청 시간과 일치하지 않는 경우 market과 date_time을 제외하고 None으로 저장
                candle_info = {
                    "market": self.query_string["market"],
                    "date_time": request_time,
                    "opening_price": None,
                    "high_price": None,
                    "low_price": None,
                    "closing_price": None,
                    "acc_price": None,
                    "acc_volume": None,
                }
            new_data.append(candle_info)

        # 데이터를 저장하고 저장된 레코드의 수를 반환
        created_objects = UpbitData.objects.bulk_create([UpbitData(**data) for data in new_data])
        return len(created_objects)

    def _get_column_data_from_db(self, column_name=None):
        """
        데이터베이스에서 컬럼 데이터를 가져오는 함수
        """
        try:
            start_time = datetime.strptime(settings.UPBIT_START_DATE, "%Y-%m-%dT%H:%M:%S%z")

            query = UpbitData.objects.annotate(
                minute=TruncMinute("date_time")
            ).order_by("minute")
            # 특정 컬럼이 필요할 경우 컬럼 데이터를 가져오는 코드
            if column_name:
                column_datas = query.values_list("minute", column_name, flat=False)
            else:
                column_datas = query.values_list("minute", flat=True)

            return list(column_datas)

        except Exception as e:
            self.logger.error(f"Error fetching column data from DB: {e}")
            return []

    def _get_missing_time_intervals(self):
        """
        데이터베이스에 없는 시간대를 가져오는 함수
        """

        start_time = datetime.strptime(settings.UPBIT_START_DATE, "%Y-%m-%dT%H:%M:%S%z")
        current_time = datetime.now(self.kst)

        # 데이터베이스에서 존재하는 시간을 가져옴
        existing_times = set(self._get_column_data_from_db())
        existing_times = {time.replace(tzinfo=self.kst) for time in existing_times}

        all_minutes = set()
        current_time_iter = start_time

        # 모든 분 단위의 시간을 계산하여 all_minutes 집합에 추가
        while current_time_iter <= current_time:
            all_minutes.add(current_time_iter)
            current_time_iter += timedelta(minutes=1)

        # 이미 존재하는 시간을 제외한 누락된 시간대 계산
        missing_times = sorted(all_minutes - existing_times)

        count_time = 1
        missing_time_groups = []

        # missing_times를 순회하며 그룹화
        for current, previous in zip(missing_times[1:], missing_times[:-1]):
            if count_time == 200:
                # 200개 단위로 그룹화
                current_iso = (current + timedelta(seconds=20)).strftime('%Y-%m-%dT%H:%M:%S') + "+09:00"
                missing_time_groups.append((current_iso, count_time))
                count_time = 1
                continue

            # 연속적인 시간대가 누락된 경우 count_time을 증가시킴
            if (current - previous).total_seconds() / 60 <= 1:
                count_time += 1
            else:
                # 연속적이지 않으면 그룹을 종료하고 새 그룹을 시작
                current_iso = (current + timedelta(seconds=20)).strftime('%Y-%m-%dT%H:%M:%S') + "+09:00"
                missing_time_groups.append((current_iso, count_time))
                print(f"current_iso: {current_iso}, count_time: {count_time}")
                count_time = 1

        # 마지막 남은 그룹 처리
        if count_time > 1:
            last_iso = (missing_times[-1] + timedelta(seconds=20)).strftime('%Y-%m-%dT%H:%M:%S') + "+09:00"
            missing_time_groups.append((last_iso, count_time - 1))

        return missing_time_groups


    def _save_to_json(self, filename, data):
        """
        데이터를 JSON 파일로 저장하는 함수
        """
        # log 디렉토리 경로 설정
        log_dir = os.path.join(os.path.dirname(__file__), 'log')
        os.makedirs(log_dir, exist_ok=True)  # log 디렉토리가 없으면 생성

        # 파일 경로 설정
        file_path = os.path.join(log_dir, filename)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
