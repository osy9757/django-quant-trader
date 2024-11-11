from django.test import TestCase
from .services import UpbitDataProvider
from unittest.mock import patch, MagicMock
from data_provider.models import UpbitData  
import pytz
from datetime import datetime, timedelta
import time as t
import json
import redis

class UpbitDataProviderTest(TestCase):
    
    def setUp(self):
        self.provider = UpbitDataProvider(currency="BTC")
        self.kst = pytz.timezone('Asia/Seoul')
        self.start_time = datetime.strptime("2024-10-19T05:10:00+09:00", "%Y-%m-%dT%H:%M:%S%z")
        
        # 쿼리 조건과 일치하는 테스트 데이터 생성
        for i in range(5):
            UpbitData.objects.create(
                market=self.provider.query_string["market"],
                date_time=self.start_time + timedelta(minutes=i),
                opening_price=10000 + i,
                high_price=10000 + i,
                low_price=10000 + i,
                closing_price=10000 + i,
                acc_price=1000 + i,
                acc_volume=10 + i
            )
        UpbitData.objects.create(
            market=self.provider.query_string["market"],
            date_time=self.start_time + timedelta(minutes=6),
            opening_price=10000 + 5,
            high_price=10000 + 5,
            low_price=10000 + 5,
            closing_price=10000 + 5,
            acc_price=1000 + 5,
            acc_volume=10 + 5
        )

    def test_get_info(self):
        saved_count, data = self.provider.get_info()
        
        self.assertIsInstance(saved_count, int, "saved_count should be an integer")
        self.assertGreater(saved_count, 0, "No data was saved.")
        self.assertTrue(UpbitData.objects.filter(market=self.provider.query_string["market"]).exists())

    def test_specific_time_get_info(self):
        saved_count, data = self.provider.get_info(to_time="2024-10-15T09:51:01+09:00", count=1)

        print("Data:", data)
        
        self.assertIsInstance(saved_count, int, "saved_count should be an integer")
        self.assertGreater(saved_count, 0, "No data was saved.")
        self.assertTrue(UpbitData.objects.filter(market=self.provider.query_string["market"]).exists())

    def test_get_data_from_upbit(self):
        try:
            data = self.provider._UpbitDataProvider__get_data_from_upbit(market="KRW-BTC", count=1)
            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)
            print("Data received:", data)
        except Exception as e:
            self.fail(f"Real API call failed with exception: {e}")

    def test_get_column_data_from_db(self):
        # 비공개 메서드 접근
        column_data = list(self.provider._get_column_data_from_db())

        start_times = [
                datetime.strptime("2024-10-19T05:10:00+09:00", "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None),
                # 이와 유사하게 여러 datetime 객체가 있다고 가정
            ]
        
        start_times_set = set(start_times)

        print("Formatted column data:", column_data)

        filtered_column_data = [time for time in column_data if time not in start_times_set]

        print("Filtered column data:", filtered_column_data)

    def test_get_missing_time_intervals(self):
        # 데이터가 없는 시간 구간을 가져오는 테스트
        missing_time_groups = self.provider._get_missing_time_intervals()
        self.assertGreater(len(missing_time_groups), 0)
        print("Missing time groups:", missing_time_groups)

    def test_save_missing_time_data(self):
        # 테스트 DB에 있는 데이터 목록 출력

        missing_time_groups = self.provider._get_missing_time_intervals()

        for missing_time, count in missing_time_groups:
            saved_count, data = self.provider.get_info(to_time=missing_time, count=count)
            t.sleep(0.5)
            self.assertGreater(saved_count, 0, f"No data was saved for {missing_time} with count {count}")


class UpbitDataProviderRedisTest(TestCase):

    def setUp(self):
        self.provider = UpbitDataProvider(currency="BTC")
        self.kst = pytz.timezone('Asia/Seoul')
        self.start_time = datetime.strptime("2024-10-19T05:10:00+09:00", "%Y-%m-%dT%H:%M:%S%z")

        # 테스트 데이터 생성
        for i in range(5):
            UpbitData.objects.create(
                market=self.provider.query_string["market"],
                date_time=self.start_time + timedelta(minutes=i),
                opening_price=10000 + i,
                high_price=10000 + i,
                low_price=10000 + i,
                closing_price=10000 + i,
                acc_price=1000 + i,
                acc_volume=10 + i
            )

        # 실제 Redis 클라이언트 설정
        self.redis_client = redis.StrictRedis(
            host='localhost',  # 실제 Redis 서버의 호스트
            port=6379,         # 실제 Redis 서버의 포트
            db=0,              # 사용할 Redis 데이터베이스 번호
            decode_responses=True
        )

    def test_sync_data_to_redis(self):
        # 메서드 호출
        self.provider._sync_data_to_redis()

        # Redis에 데이터가 올바르게 저장되었는지 확인
        for data in UpbitData.objects.all():
            key = f"upbit:{data.market}:1m:test"
            score = int(data.date_time.timestamp())
            value = json.dumps({
                "date_time": data.date_time.strftime('%Y-%m-%dT%H:%M:%S'),
                "opening_price": data.opening_price,
                "high_price": data.high_price,
                "low_price": data.low_price,
                "closing_price": data.closing_price,
                "acc_price": data.acc_price,
                "acc_volume": data.acc_volume,
            }, sort_keys=True)

            # Redis의 Sorted Set에 데이터 추가
        self.redis_client.zadd(key, {value: score})
