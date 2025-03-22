import pandas as pd
import logging
from django.utils import timezone
from django.db import connection
from django_backend.data_provider.models import UpbitData

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """
    데이터 로드 및 1분봉 데이터를 활용한 N분봉 집계 기능 제공 클래스.
    기존 기술적 분석 지표 계산 함수들은 제거하였습니다.
    """

    def __init__(self, market="KRW-BTC"):
        self.market = market
        self.logger = logger
        self.df = None  # 1분봉 캔들 데이터를 저장할 DataFrame

    def load_data(self, period=500, to=None):
        """
        주어진 개수(period)의 캔들 데이터를 로드합니다.
        
        :param period: 로드할 캔들 개수 (기본값: 500)
        :param to: 조회 종료 시점 (기본값: 현재 UTC 시간)
        :return: 캔들 데이터 DataFrame
        """
        if to is None:
            to = timezone.now()
            
        candles = UpbitData.objects.filter(
            market=self.market,
            candle_date_time_utc__lte=to
        ).order_by('-candle_date_time_utc')[:period]
        
        candle_list = list(candles.values(
            'market', 'candle_date_time_utc', 'candle_date_time_kst',
            'opening_price', 'high_price', 'low_price', 'trade_price',
            'timestamp', 'candle_acc_trade_price', 'candle_acc_trade_volume'
        ))
        
        df = pd.DataFrame(candle_list)
        df = df.sort_values('candle_date_time_utc')
        df = df.rename(columns={
            'trade_price': 'close',
            'opening_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'candle_acc_trade_volume': 'volume',
            'candle_acc_trade_price': 'value'
        })
        
        self.df = df
        self.logger.info(f"{self.market} 캔들 데이터 {len(df)}개 로드 완료")
        return df

    @staticmethod
    def dictfetchall(cursor):
        """
        커서로부터 모든 행을 dict 형태로 반환하는 헬퍼 함수.
        """
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    @staticmethod
    def get_n_minute_data_with_interpolation(market, n, m):
        """
        1분봉 데이터를 활용하여 N분봉 데이터 m개를 반환합니다.
        Null 값은 SQL 내 윈도우 함수와 COALESCE를 사용해 이전 유효 값으로 대체(interpolation)됩니다.
        
        :param market: 종목 코드 (예: 'KRW-BTC')
        :param n: 집계할 분 간격 (예: 5분봉이면 n=5)
        :param m: 반환할 집계 단위(버킷)의 개수
                  (예: n=5, m=100이면 100개의 5분봉 데이터, 즉 500분 분량의 데이터를 반환)
        :return: 집계된 N분봉 데이터 리스트
        """
        query = """
        WITH bucketed AS (
            SELECT
                date_trunc('minute', date_time)
                    + floor(extract('minute' from date_time)::int / %s) * interval '%s minute' AS bucket_time,
                market,
                min(date_time) AS min_time,
                max(date_time) AS max_time,
                max(high_price) AS high_price,
                min(low_price) AS low_price,
                sum(acc_price) AS acc_price,
                sum(acc_volume) AS acc_volume
            FROM data_provider_upbitdata
            WHERE market = %s
            GROUP BY bucket_time, market
        ),
        joined AS (
            SELECT
                b.market,
                b.bucket_time,
                ud_open.opening_price AS opening_price,
                b.high_price,
                b.low_price,
                ud_close.closing_price AS closing_price,
                b.acc_price,
                b.acc_volume
            FROM bucketed b
            JOIN data_provider_upbitdata ud_open
                ON b.market = ud_open.market AND ud_open.date_time = b.min_time
            JOIN data_provider_upbitdata ud_close
                ON b.market = ud_close.market AND ud_close.date_time = b.max_time
        )
        SELECT
            market,
            bucket_time,
            COALESCE(
                opening_price,
                LAST_VALUE(opening_price) IGNORE NULLS OVER (
                    ORDER BY bucket_time ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                )
            ) AS opening_price,
            COALESCE(
                closing_price,
                LAST_VALUE(closing_price) IGNORE NULLS OVER (
                    ORDER BY bucket_time ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                )
            ) AS closing_price,
            COALESCE(
                high_price,
                LAST_VALUE(high_price) IGNORE NULLS OVER (
                    ORDER BY bucket_time ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                )
            ) AS high_price,
            COALESCE(
                low_price,
                LAST_VALUE(low_price) IGNORE NULLS OVER (
                    ORDER BY bucket_time ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                )
            ) AS low_price,
            COALESCE(
                acc_price,
                LAST_VALUE(acc_price) IGNORE NULLS OVER (
                    ORDER BY bucket_time ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                )
            ) AS acc_price,
            COALESCE(
                acc_volume,
                LAST_VALUE(acc_volume) IGNORE NULLS OVER (
                    ORDER BY bucket_time ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                )
            ) AS acc_volume
        FROM joined
        ORDER BY bucket_time DESC
        LIMIT %s;
        """
        params = (n, n, market, m)
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            results = TechnicalAnalyzer.dictfetchall(cursor)
        return results
