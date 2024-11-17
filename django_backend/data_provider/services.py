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
import redis
from config.utils import generate_redis_key


class UpbitDataProvider:
    """
    업비트 거래소의 실시간 및 과거 거래 데이터를 제공하는 클래스
    
    NOTE: 현재 이 클래스는 Upbit 데이터 제공자만 지원합니다.
    TODO: 다른 데이터 제공자(Binance, Coinbase 등)를 지원할 수 있도록 확장 가능한 구조로 수정해야 합니다.
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

        self.redis_client = redis.StrictRedis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )

        # FIXME: 현재는 Upbit만 지원합니다. 데이터 제공자별로 URL과 설정을 다르게 가져갈 수 있도록 구조 변경 필요.
        # TODO: 데이터 제공자별 URL과 설정을 관리하는 별도의 설정 파일이나 클래스 구현 고려.

    def get_info(self, market="KRW-BTC", to_time=None, count=1):
        """
        업비트 API에서 데이터를 가져와 저장
        
        NOTE: 현재는 market 인자를 직접 받아옵니다.
        TODO: 다양한 데이터 제공자를 지원할 수 있도록 파라미터 구조를 확장해야 합니다.
        """
        # to_time이 None이면 현재 시간을 기본값으로 설정
        if to_time is None:
            to_time = datetime.now(self.kst).replace(second=10).strftime('%Y-%m-%dT%H:%M:%S%z')    
            to_time = to_time[:-2] + ':' + to_time[-2:]  # NOTE: 문자열 포맷이 필요해서 수정하는 부분입니다. 최적화 가능성 검토 필요.

        data = self.__get_data_from_upbit(market, to_time, count)
        saved_count = self.__save_data_to_db(data, to_time, count)

        return saved_count, data

    def __get_data_from_upbit(self, market="KRW-BTC", to_time=None, count=1):
        """
        업비트 API에서 데이터를 가져오는 함수
        
        TODO: 이 함수는 Upbit API에만 국한됩니다. 다른 데이터 제공자를 추가하기 위해 추상화된 인터페이스나
        클래스 구조를 도입할 필요가 있습니다.
        FIXME: API 호출 시 오류 핸들링이 추가적으로 필요할 수 있음. 요청 실패 시 재시도 로직 검토 필요.
        """
        self.query_string["market"] = market
        self.query_string["count"] = count
        self.query_string["to"] = to_time

        response = requests.get(self.URL, params=self.query_string)
        response.raise_for_status()
        data = response.json()

        if not data or len(data) == 0:
            # FIXME: API에서 데이터가 비어 있는 경우에 대한 추가 로직 필요. 특정 시나리오에서 경고 로그 추가.
            raise ValueError("No data received from Upbit API")

        return data

    def __save_data_to_db(self, data, to_time, count):
        """
        데이터를 데이터베이스에 저장하는 함수
        
        FIXME: 중복 저장 방지를 위해 데이터베이스에 존재 여부를 먼저 확인할 필요가 있음.
        TODO: 데이터 저장 로직을 제공자별로 다르게 구현할 수 있도록 수정해야 할 수 있음.
        NOTE: 현재는 Upbit 데이터에 맞춰 저장하고 있으나, 다른 제공자에 대해 확장할 때 데이터 형식 조정이 필요.
        """
        new_data = []

        if isinstance(to_time, str):
            to_time = datetime.strptime(to_time, '%Y-%m-%dT%H:%M:%S+09:00')
        to_time = to_time.replace(second=0)
        to_time = self.kst.localize(to_time)

        # TODO: 요청 시간을 생성하는 로직을 공통 모듈로 추출해 재사용성을 높일 수 있음.
        requested_times = [to_time - timedelta(minutes=i) for i in range(count)]

        data_times = {self.kst.localize(datetime.strptime(candle["candle_date_time_kst"], "%Y-%m-%dT%H:%M:%S")): candle for candle in data}

        for request_time in requested_times:
            matching_data = data_times.get(request_time)

            if matching_data:
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
                # NOTE: 누락된 데이터의 경우 None으로 저장됨. 나중에 복구나 보완을 위해 로그 추가 필요.
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

        # TODO: 성능 최적화를 위해 bulk_create에 대해 에러 핸들링 및 로깅 추가 필요.
        created_objects = UpbitData.objects.bulk_create([UpbitData(**data) for data in new_data])
        return len(created_objects)

    def _get_column_data_from_db(self, column_name=None):
        """
        데이터베이스에서 컬럼 데이터를 가져오는 함수
        
        NOTE: 특정 컬럼 데이터를 가져오며, 현재는 datetime 기반으로 작동합니다.
        TODO: 데이터 필터링 및 컬럼명 검증 로직 추가 필요.
        """
        try:
            start_time = datetime.strptime(settings.UPBIT_START_DATE, "%Y-%m-%dT%H:%M:%S%z")

            query = UpbitData.objects.annotate(
                minute=TruncMinute("date_time")
            ).order_by("minute")
            # NOTE: 특정 컬럼을 선택할 수 있도록 구현됨.
            if column_name:
                column_datas = query.values_list("minute", column_name, flat=False)
            else:
                column_datas = query.values_list("minute", flat=True)

            return list(column_datas)

        except Exception as e:
            # FIXME: 특정 예외 상황에 대한 핸들링 추가 필요 (ex: 데이터베이스 연결 실패)
            self.logger.error(f"Error fetching column data from DB: {e}")
            return []

    def _get_missing_time_intervals(self):
        """
        데이터베이스에 없는 시간대를 가져오는 함수
        
        TODO: 대규모 데이터의 경우 성능 최적화를 위해 시간대 계산 알고리즘 개선 필요.
        NOTE: 현재는 전체 데이터를 메모리에 로드하여 시간대 차이를 계산합니다.
        """
        start_time = datetime.strptime(settings.UPBIT_START_DATE, "%Y-%m-%dT%H:%M:%S%z")
        current_time = datetime.now(self.kst)

        existing_times = set(self._get_column_data_from_db())

        all_minutes = []
        current_time_iter = start_time

        while current_time_iter <= current_time:
            all_minutes.append(current_time_iter.replace(tzinfo=None))
            current_time_iter += timedelta(minutes=1)
        
        all_minutes_set = set(all_minutes)
        missing_times = sorted([time for time in all_minutes_set if time not in existing_times])

        count_time = 1
        missing_time_groups = []

        for current, previous in zip(missing_times[1:], missing_times[:-1]):
            if count_time == 200:
                # NOTE: 그룹 크기 200을 기준으로 나눕니다. 최적화 가능성 검토 필요.
                current_iso = (current + timedelta(seconds=20)).strftime('%Y-%m-%dT%H:%M:%S') + "+09:00"
                missing_time_groups.append((current_iso, count_time))
                count_time = 1
                continue

            if (current - previous).total_seconds() / 60 <= 1:
                count_time += 1
            else:
                previous_iso = (previous + timedelta(seconds=20)).strftime('%Y-%m-%dT%H:%M:%S') + "+09:00"
                missing_time_groups.append((previous_iso, count_time))
                count_time = 1

        if count_time > 1:
            last_iso = (missing_times[-1] + timedelta(seconds=20)).strftime('%Y-%m-%dT%H:%M:%S') + "+09:00"
            missing_time_groups.append((last_iso, count_time - 1))

        return missing_time_groups

    def _save_to_json(self, filename, data):
        """
        데이터를 JSON 파일로 저장하는 함수
        
        TODO: 파일 저장 로직에 대해 예외 핸들링 추가 필요. 파일 쓰기 실패 시 경고 로깅 추가.
        NOTE: log 디렉토리에 데이터를 저장합니다.
        """
        log_dir = os.path.join(os.path.dirname(__file__), 'log')
        os.makedirs(log_dir, exist_ok=True)

        file_path = os.path.join(log_dir, filename)

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def _save_to_redis(self, data):
        """
        data를 redis에 저장하는 함수
        
        TODO: Redis에 데이터를 저장할 때 TTL 설정이나 만료 정책 추가 검토 필요.
        FIXME: 대량의 데이터를 저장할 때 성능 문제가 발생할 수 있으므로 최적화 필요.
        """
        for candle in data:
            redis_key = generate_redis_key('upbit', self.query_string['market'])
            score = int(datetime.strptime(candle["candle_date_time_kst"], "%Y-%m-%dT%H:%M:%S").timestamp())
            value = json.dumps({
                "date_time": candle["candle_date_time_kst"],
                "opening_price": candle["opening_price"],
                "high_price": candle["high_price"],
                "low_price": candle["low_price"],
                "closing_price": candle["trade_price"],
                "acc_price": candle["candle_acc_trade_price"],
                "acc_volume": candle["candle_acc_trade_volume"],
            }, sort_keys=True)
            self.redis_client.zadd(redis_key, {value: score})

    def _sync_data_to_redis(self, save_days=settings.REDIS_SAVE_DAYS):
        """
        데이터베이스의 데이터를 Redis에 동기화하는 함수
        
        TODO: 동기화 시점의 효율성을 높이기 위해 스케줄링 로직 개선 필요.
        NOTE: 데이터 갱신 시 누락된 시간대를 복구하는데 사용됨.
        """
        try:
            now = datetime.now()
            save_days_ago = now - timedelta(days=save_days)
            data_gaps = []

            db_data = UpbitData.objects.filter(date_time__gte=save_days_ago).values_list('date_time', flat=True)

            redis_key = generate_redis_key('upbit', self.query_string['market'])
            redis_timestamps = self.redis_client.zrangebyscore(
                redis_key, int(save_days_ago.timestamp()), int(now.timestamp()), withscores=True
            )
            redis_timestamps = {int(score) for _, score in redis_timestamps}

            for dt in db_data:
                timestamp = int(dt.timestamp())
                if timestamp not in redis_timestamps:
                    data_gaps.append(dt)

            for dt in data_gaps:
                data = UpbitData.objects.get(date_time=dt)
                value = json.dumps({
                    "date_time": data.date_time.strftime('%Y-%m-%dT%H:%M:%S'),
                    "opening_price": data.opening_price,
                    "high_price": data.high_price,
                    "low_price": data.low_price,
                    "closing_price": data.closing_price,
                    "acc_price": data.acc_price,
                    "acc_volume": data.acc_volume,
                }, sort_keys=True)
                score = int(data.date_time.timestamp())
                self.redis_client.zadd(redis_key, {value: score})

            self.logger.info("Data successfully synced to Redis.")
        except Exception as e:
            # FIXME: 구체적인 예외 상황에 대한 로그 추가 필요 (ex: Redis 연결 실패)
            self.logger.error(f'Error syncing data to Redis; {e}')
