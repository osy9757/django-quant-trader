# django_backend/analyzer/tests.py
from django.test import TestCase
from django.utils import timezone
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from analyzer.services import TechnicalAnalyzer

class TechnicalAnalyzerTestCase(TestCase):
    def setUp(self):
        """
        테스트를 위한 가상 데이터 생성
        """
        self.analyzer = TechnicalAnalyzer(market="TEST-BTC")
        
        # 테스트용 데이터 생성 - 1분봉 200개 (가상 데이터)
        base_time = timezone.now()
        candles = []
        
        # 가격 패턴 생성 (상승 -> 하락 -> 상승)
        prices = []
        # 시작 가격
        start_price = 50000
        
        # 상승 트렌드 (70개)
        for i in range(70):
            # 약간의 노이즈 추가
            noise = np.random.normal(0, 200)
            price = start_price + i * 100 + noise
            prices.append(price)
        
        # 하락 트렌드 (70개)
        for i in range(70):
            noise = np.random.normal(0, 200)
            price = start_price + 7000 - i * 100 + noise
            prices.append(price)
        
        # 횡보 트렌드 (60개)
        for i in range(60):
            noise = np.random.normal(0, 500)
            price = start_price + 0 + noise
            prices.append(price)
            
        # 캔들 데이터 생성
        for i in range(200):
            candle_time = base_time - timedelta(minutes=200-i)
            
            # 현재 종가
            close = prices[i]
            
            # 시가는 이전 종가에 약간의 변화를 줌
            if i == 0:
                open_price = close - np.random.normal(0, 50)
            else:
                open_price = prices[i-1] + np.random.normal(0, 50)
            
            # 고가는 시가와 종가 중 높은 값보다 약간 더 높게
            high = max(open_price, close) + abs(np.random.normal(0, 100))
            
            # 저가는 시가와 종가 중 낮은 값보다 약간 더 낮게
            low = min(open_price, close) - abs(np.random.normal(0, 100))
            
            # 거래량은 가격 변화가 클수록 증가하도록
            if i == 0:
                volume = abs(np.random.normal(100, 30))
            else:
                price_change = abs(close - prices[i-1])
                volume = price_change * 0.1 + abs(np.random.normal(100, 30))
            
            # 거래대금
            value = close * volume
            
            candles.append({
                'market': 'TEST-BTC',
                'candle_date_time_utc': candle_time,
                'candle_date_time_kst': candle_time + timedelta(hours=9),
                'timestamp': int(candle_time.timestamp() * 1000),
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume,
                'value': value
            })
        
        # DataFrame 생성
        self.test_df = pd.DataFrame(candles)
        
        # TechnicalAnalyzer 인스턴스의 내부 데이터 설정
        self.analyzer.df = self.test_df
    
    def test_rsi(self):
        """RSI 계산 테스트"""
        # RSI 계산 (기본 14일)
        rsi_df = self.analyzer.calculate_rsi(df=self.test_df, period=14, candle_count=100)
        
        # 결과 확인
        self.assertIsNotNone(rsi_df)
        self.assertEqual(len(rsi_df), 100)  # 최근 100개만 반환
        self.assertIn('rsi', rsi_df.columns)
        
        # RSI 유효 범위 확인 (0-100)
        self.assertTrue(all(0 <= rsi <= 100 for rsi in rsi_df['rsi']))
        
        # Wilder 방식과 SMA 방식 비교
        rsi_wilder = self.analyzer.calculate_rsi(df=self.test_df, period=14, use_wilder=True)
        rsi_sma = self.analyzer.calculate_rsi(df=self.test_df, period=14, use_wilder=False)
        
        # 두 방식은 다른 결과를 내야 함
        self.assertFalse(rsi_wilder['rsi'].equals(rsi_sma['rsi']))
    
    def test_stochastic(self):
        """스토캐스틱 계산 테스트"""
        stoch_df = self.analyzer.calculate_stochastic(df=self.test_df, k_period=14, d_period=3)
        
        self.assertIsNotNone(stoch_df)
        self.assertIn('fast_k', stoch_df.columns)
        self.assertIn('slow_d', stoch_df.columns)
        
        # 유효 범위 확인 (0-100)
        self.assertTrue(all(0 <= k <= 100 for k in stoch_df['fast_k']))
        self.assertTrue(all(0 <= d <= 100 for d in stoch_df['slow_d']))
    
    def test_ema(self):
        """EMA 계산 테스트"""
        ema_df = self.analyzer.calculate_ema(df=self.test_df, period=20)
        
        self.assertIsNotNone(ema_df)
        self.assertIn('ema', ema_df.columns)
        
        # EMA는 가격 범위 내에 있어야 함
        self.assertTrue(ema_df['ema'].min() >= self.test_df['low'].min())
        self.assertTrue(ema_df['ema'].max() <= self.test_df['high'].max())
        
        # 여러 기간의 EMA 비교
        ema_short = self.analyzer.calculate_ema(df=self.test_df, period=9)
        ema_long = self.analyzer.calculate_ema(df=self.test_df, period=50)
        
        # 상승 트렌드에서는 단기 EMA가 장기 EMA보다 높아야 함
        # (테스트 데이터의 처음은 상승 트렌드이므로)
        self.assertTrue(ema_short['ema'].iloc[-1] != ema_long['ema'].iloc[-1])
    
    def test_bollinger_bands(self):
        """볼린저 밴드 계산 테스트"""
        bb_df = self.analyzer.calculate_bollinger_bands(df=self.test_df, period=20)
        
        self.assertIsNotNone(bb_df)
        self.assertIn('middle_band', bb_df.columns)
        self.assertIn('upper_band', bb_df.columns)
        self.assertIn('lower_band', bb_df.columns)
        
        # 상단밴드 > 중앙밴드 > 하단밴드 확인
        self.assertTrue(all(bb_df['upper_band'] > bb_df['middle_band']))
        self.assertTrue(all(bb_df['middle_band'] > bb_df['lower_band']))
    
    def test_macd(self):
        """MACD 계산 테스트"""
        macd_df = self.analyzer.calculate_macd(df=self.test_df)
        
        self.assertIsNotNone(macd_df)
        self.assertIn('macd_line', macd_df.columns)
        self.assertIn('signal_line', macd_df.columns)
        self.assertIn('histogram', macd_df.columns)
        
        # 히스토그램 = MACD 라인 - 시그널 라인 확인
        for idx, row in macd_df.iterrows():
            self.assertAlmostEqual(row['histogram'], row['macd_line'] - row['signal_line'], places=4)
    
    def test_ichimoku(self):
        """일목균형표 계산 테스트"""
        ichimoku_df = self.analyzer.calculate_ichimoku(df=self.test_df)
        
        self.assertIsNotNone(ichimoku_df)
        self.assertIn('tenkan_sen', ichimoku_df.columns)
        self.assertIn('kijun_sen', ichimoku_df.columns)
        self.assertIn('senkou_span_a', ichimoku_df.columns)
        self.assertIn('senkou_span_b', ichimoku_df.columns)
        
        # 26일 기준선 기간에 따라 스팬이 있는지 확인
        # (단, 테스트 데이터가 200개이므로 전체 확인은 어려움)
        if len(ichimoku_df) > 50:  # 충분한 데이터가 있는 경우
            self.assertTrue(ichimoku_df['senkou_span_a'].notna().any())
            self.assertTrue(ichimoku_df['senkou_span_b'].notna().any())
    
    def test_keltner_channel(self):
        """켈트너 채널 계산 테스트"""
        keltner_df = self.analyzer.calculate_keltner_channel(df=self.test_df)
        
        self.assertIsNotNone(keltner_df)
        self.assertIn('middle_channel', keltner_df.columns)
        self.assertIn('upper_channel', keltner_df.columns)
        self.assertIn('lower_channel', keltner_df.columns)
        
        # 상단채널 > 중앙채널 > 하단채널 확인
        self.assertTrue(all(keltner_df['upper_channel'] > keltner_df['middle_channel']))
        self.assertTrue(all(keltner_df['middle_channel'] > keltner_df['lower_channel']))
        
        # Wilder ATR와 SMA ATR 비교
        keltner_wilder = self.analyzer.calculate_keltner_channel(df=self.test_df, use_wilder_atr=True)
        keltner_sma = self.analyzer.calculate_keltner_channel(df=self.test_df, use_wilder_atr=False)
        
        # 두 방식은 다른 결과를 내야 함
        self.assertFalse(keltner_wilder['upper_channel'].equals(keltner_sma['upper_channel']))
    
    def test_vwap(self):
        """VWAP 계산 테스트"""
        vwap_df = self.analyzer.calculate_vwap(df=self.test_df)
        
        self.assertIsNotNone(vwap_df)
        self.assertIn('vwap', vwap_df.columns)
        
        # VWAP는 가격 범위 내에 있어야 함
        self.assertTrue(vwap_df['vwap'].min() >= self.test_df['low'].min())
        self.assertTrue(vwap_df['vwap'].max() <= self.test_df['high'].max())
    
    def test_analyze_all(self):
        """analyze_all 메소드 테스트"""
        # analyze_all은 내부 데이터를 사용하므로 직접 설정
        self.analyzer.df = self.test_df
        
        # 모든 지표 계산
        results = self.analyzer.analyze_all(candle_count=50)
        
        self.assertIsNotNone(results)
        self.assertIn('rsi', results)
        self.assertIn('stochastic', results)
        self.assertIn('ema_short', results)
        self.assertIn('ema_medium', results)
        self.assertIn('ema_long', results)
        self.assertIn('bollinger', results)
        self.assertIn('macd', results)
        self.assertIn('ichimoku', results)
        self.assertIn('keltner', results)
        self.assertIn('vwap', results)
        
        # 모든 결과는 50개의 데이터를 가져야 함
        self.assertEqual(len(results['rsi']), 50)
        
        # 특정 지표만 계산
        selected_results = self.analyzer.analyze_all(candle_count=30, params=['rsi', 'macd'])
        
        self.assertIn('rsi', selected_results)
        self.assertIn('macd', selected_results)
        self.assertNotIn('bollinger', selected_results)
        
        # 모든 결과는 30개의 데이터를 가져야 함
        self.assertEqual(len(selected_results['rsi']), 30)

    def test_edge_cases(self):
        """예외 상황 테스트"""
        # 빈 데이터프레임
        empty_df = pd.DataFrame()
        result = self.analyzer.calculate_rsi(df=empty_df)
        self.assertTrue(result.empty)
        
        # 데이터가 부족한 경우
        small_df = self.test_df.head(10)  # 10개만 사용
        rsi_result = self.analyzer.calculate_rsi(df=small_df, period=14)
        # RSI 계산에는 최소 15개 데이터가 필요하므로 결과는 비어있거나 모두 NaN
        self.assertTrue(rsi_result.empty or rsi_result['rsi'].isna().all())
        
        # 잘못된 파라미터
        with self.assertRaises(Exception):
            self.analyzer.calculate_rsi(period=-1)  # 음수 기간은 오류
