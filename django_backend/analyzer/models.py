# django_backend/analyzer/models.py
from django.db import models
from django_backend.data_provider.models import UpbitData

class TechnicalIndicator(models.Model):
    """
    기술적 지표(Technical Indicator)의 기본 모델
    모든 기술적 지표는 이 모델을 상속받아 구현
    """
    market = models.CharField(max_length=20)
    candle_date_time_utc = models.DateTimeField()
    candle_date_time_kst = models.DateTimeField()
    timestamp = models.BigIntegerField()
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['market', 'candle_date_time_utc']),
            models.Index(fields=['timestamp']),
        ]

class RSI(TechnicalIndicator):
    """
    상대강도지수(Relative Strength Index) 모델
    RSI = 100 - (100 / (1 + RS))
    RS = 평균 상승폭 / 평균 하락폭
    """
    period = models.IntegerField()  # RSI 계산 기간 (일반적으로 14)
    value = models.FloatField()     # RSI 값 (0-100)

    class Meta:
        unique_together = ('market', 'candle_date_time_utc', 'period')
        indexes = [
            models.Index(fields=['market', 'period']),
        ]

class Stochastic(TechnicalIndicator):
    """
    스토캐스틱 오실레이터(Stochastic Oscillator) 모델
    K% = (현재가 - n기간 최저가) / (n기간 최고가 - n기간 최저가) * 100
    D% = K%의 m기간 이동평균
    """
    k_period = models.IntegerField()  # K% 계산 기간 (일반적으로 14)
    d_period = models.IntegerField()  # D% 계산 기간 (일반적으로 3)
    k_value = models.FloatField()     # K% 값 (0-100)
    d_value = models.FloatField()     # D% 값 (0-100)

    class Meta:
        unique_together = ('market', 'candle_date_time_utc', 'k_period', 'd_period')

class EMA(TechnicalIndicator):
    """
    지수이동평균(Exponential Moving Average) 모델
    EMA = 이전 EMA + (현재가 - 이전 EMA) * (2 / (기간 + 1))
    """
    period = models.IntegerField()  # EMA 계산 기간
    value = models.FloatField()     # EMA 값

    class Meta:
        unique_together = ('market', 'candle_date_time_utc', 'period')

class BollingerBands(TechnicalIndicator):
    """
    볼린저 밴드(Bollinger Bands) 모델
    중앙선 = n기간 이동평균
    상단선 = 중앙선 + (n기간 표준편차 * k)
    하단선 = 중앙선 - (n기간 표준편차 * k)
    """
    period = models.IntegerField()      # 계산 기간 (일반적으로 20)
    deviation = models.FloatField()     # 표준편차 승수 (일반적으로 2)
    upper_band = models.FloatField()    # 상단선
    middle_band = models.FloatField()   # 중앙선
    lower_band = models.FloatField()    # 하단선
    bandwidth = models.FloatField()     # 밴드폭 (상단-하단)/중앙

    class Meta:
        unique_together = ('market', 'candle_date_time_utc', 'period', 'deviation')

class MACD(TechnicalIndicator):
    """
    MACD(Moving Average Convergence Divergence) 모델
    MACD Line = 단기 EMA - 장기 EMA
    Signal Line = MACD Line의 n기간 EMA
    Histogram = MACD Line - Signal Line
    """
    short_period = models.IntegerField()  # 단기 EMA 기간 (일반적으로 12)
    long_period = models.IntegerField()   # 장기 EMA 기간 (일반적으로 26)
    signal_period = models.IntegerField() # 시그널 라인 기간 (일반적으로 9)
    macd_line = models.FloatField()       # MACD 라인 값
    signal_line = models.FloatField()     # 시그널 라인 값
    histogram = models.FloatField()       # 히스토그램 값

    class Meta:
        unique_together = ('market', 'candle_date_time_utc', 'short_period', 'long_period', 'signal_period')

class Ichimoku(TechnicalIndicator):
    """
    일목균형표(Ichimoku Kinko Hyo) 모델
    전환선(Tenkan-sen) = (n기간 최고가 + n기간 최저가) / 2 (일반적으로 n=9)
    기준선(Kijun-sen) = (n기간 최고가 + n기간 최저가) / 2 (일반적으로 n=26)
    선행스팬1(Senkou Span A) = (전환선 + 기준선) / 2 (26기간 이후)
    선행스팬2(Senkou Span B) = (n기간 최고가 + n기간 최저가) / 2 (일반적으로 n=52, 26기간 이후)
    후행스팬(Chikou Span) = 현재 종가 (26기간 이전)
    """
    tenkan_period = models.IntegerField()  # 전환선 기간 (일반적으로 9)
    kijun_period = models.IntegerField()   # 기준선 기간 (일반적으로 26)
    senkou_b_period = models.IntegerField()  # 선행스팬B 기간 (일반적으로 52)
    tenkan_sen = models.FloatField()       # 전환선
    kijun_sen = models.FloatField()        # 기준선
    senkou_span_a = models.FloatField()    # 선행스팬1
    senkou_span_b = models.FloatField()    # 선행스팬2
    chikou_span = models.FloatField()      # 후행스팬

    class Meta:
        unique_together = ('market', 'candle_date_time_utc', 'tenkan_period', 'kijun_period', 'senkou_b_period')

class KeltnerChannel(TechnicalIndicator):
    """
    켈트너 채널(Keltner Channel) 모델
    중앙선 = n기간 EMA
    상단선 = 중앙선 + (n기간 ATR * 승수)
    하단선 = 중앙선 - (n기간 ATR * 승수)
    ATR = Average True Range
    """
    ema_period = models.IntegerField()    # EMA 기간 (일반적으로 20)
    atr_period = models.IntegerField()    # ATR 기간 (일반적으로 10)
    multiplier = models.FloatField()      # ATR 승수 (일반적으로 2)
    upper_channel = models.FloatField()   # 상단 채널
    middle_channel = models.FloatField()  # 중앙선
    lower_channel = models.FloatField()   # 하단 채널

    class Meta:
        unique_together = ('market', 'candle_date_time_utc', 'ema_period', 'atr_period', 'multiplier')

class VWAP(TechnicalIndicator):
    """
    거래량가중평균가격(Volume Weighted Average Price) 모델
    VWAP = Σ(가격 * 거래량) / Σ(거래량)
    """
    period = models.IntegerField()  # 계산 기간
    value = models.FloatField()     # VWAP 값

    class Meta:
        unique_together = ('market', 'candle_date_time_utc', 'period')

# Create your models here.
