  # django_backend/data_provider/models.py
from django.db import models

class UpbitData(models.Model):
    # 종목 코드 (예: BTC, ETH 등)
    market = models.CharField(max_length=10)
    # UTC 기준 캔들 시각 (db_index=True로 검색 성능 최적화)
    date_time = models.DateTimeField(db_index=True)
    # 시가 (캔들이 시작할 때의 가격)
    opening_price = models.FloatField(null=True)
    # 고가 (해당 캔들에서 가장 높은 가격)
    high_price = models.FloatField(null=True)
    # 저가 (해당 캔들에서 가장 낮은 가격)
    low_price = models.FloatField(null=True)
    # 종가 (캔들이 끝날 때의 가격)
    closing_price = models.FloatField(null=True)
    # 누적 거래 금액 (해당 캔들 동안의 총 거래 금액)
    acc_price = models.FloatField(null=True)
    # 누적 거래량 (해당 캔들 동안의 총 거래량)
    acc_volume = models.FloatField(null=True)

    class Meta:
        # 'market'과 'date_time' 조합의 중복을 방지 (고유 조건 설정)
        unique_together = ('market', 'date_time')
        # 기본 정렬 기준을 'date_time'으로 설정
        ordering = ['date_time']
        # 해당 모델을 포함하는 Django 앱의 이름 설정
        app_label = 'data_provider'

    def __str__(self):
        # 객체의 문자열 표현으로 'market'과 'date_time' 반환
        return f"{self.market} at {self.date_time}"
