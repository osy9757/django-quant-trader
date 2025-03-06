# django_backend/analyzer/services.py
import pandas as pd
import numpy as np
from django.utils import timezone
from django_backend.data_provider.models import UpbitData
import logging

logger = logging.getLogger(__name__)

class TechnicalAnalyzer:
    """
    기술적 분석 도구 클래스
    - RSI, 스토캐스틱, EMA, 볼린저밴드, MACD, 일목균형표, 켈트너채널, VWAP 기술 지표 계산
    - 1분봉 데이터를 사용하여 분석
    """
    
    def __init__(self, market="KRW-BTC"):
        """
        초기화 함수
        :param market: 분석 대상 마켓 코드 (예: KRW-BTC)
        """
        self.market = market
        self.logger = logger
        self.df = None  # 캔들 데이터를 저장할 DataFrame
    
    def load_data(self, period=500, to=None):
        """
        한 번에 충분한 양의 캔들 데이터를 로드
        :param period: 로드할 캔들 개수 (default: 500)
        :param to: 조회 종료 시점 (default: 현재 시간)
        :return: 로드된 캔들 데이터 DataFrame
        """
        if to is None:
            # 현재 UTC 시간 기준 (업비트 데이터는 UTC 기준으로 저장됨)
            to = timezone.now()
            
        candles = UpbitData.objects.filter(
            market=self.market,
            candle_date_time_utc__lte=to  # UTC 기준 시간으로 필터링
        ).order_by('-candle_date_time_utc')[:period]
        
        # 리스트로 변환 후 DataFrame 생성
        candle_list = list(candles.values(
            'market', 'candle_date_time_utc', 'candle_date_time_kst',
            'opening_price', 'high_price', 'low_price', 'trade_price',
            'timestamp', 'candle_acc_trade_price', 'candle_acc_trade_volume'
        ))
        
        # DataFrame으로 변환
        df = pd.DataFrame(candle_list)
        
        # 날짜 기준 오름차순 정렬 (오래된 날짜 -> 최신 날짜)
        df = df.sort_values('candle_date_time_utc')
        
        # 컬럼명 변경
        df = df.rename(columns={
            'trade_price': 'close',
            'opening_price': 'open',
            'high_price': 'high',
            'low_price': 'low',
            'candle_acc_trade_volume': 'volume',
            'candle_acc_trade_price': 'value'
        })
        
        # 인스턴스 변수에 저장
        self.df = df
        
        self.logger.info(f"{self.market} 캔들 데이터 {len(df)}개 로드 완료")
        return df
    
    def calculate_rsi(self, df=None, period=14, candle_count=100, use_wilder=True):
        """
        RSI(Relative Strength Index) 계산
        :param df: 사용할 DataFrame (default: None - 내부 데이터 사용)
        :param period: RSI 계산 기간 (default: 14)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :param use_wilder: Wilder's 방식 사용 여부 (default: True)
        :return: RSI 값이 포함된 DataFrame
        """
        # DataFrame이 전달되지 않았다면 내부 데이터 사용
        if df is None:
            if self.df is None:
                self.logger.warning("데이터가 로드되지 않음. load_data() 먼저 호출 필요")
                return None
            df = self.df.copy()
        
        # 가격 변화 계산
        df['price_diff'] = df['close'].diff()
        
        # 상승/하락 구분
        df['gain'] = df['price_diff'].clip(lower=0)
        df['loss'] = -df['price_diff'].clip(upper=0)
        
        if use_wilder:
            # Wilder's RSI 방식 (지수평활화 방식)
            # 첫 번째 평균은 단순 평균으로 계산
            avg_gain = df['gain'].rolling(window=period).mean()
            avg_loss = df['loss'].rolling(window=period).mean()
            
            # 첫 번째 유효값부터 Wilder 방식 적용
            first_valid = avg_gain.first_valid_index()
            if first_valid is not None:
                for i in range(df.index.get_loc(first_valid) + 1, len(df)):
                    avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period-1) + df['gain'].iloc[i]) / period
                    avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period-1) + df['loss'].iloc[i]) / period
        else:
            # 단순이동평균 방식의 RSI
            avg_gain = df['gain'].rolling(window=period).mean()
            avg_loss = df['loss'].rolling(window=period).mean()
        
        # RSI 계산
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # NaN 값 제거하고 최근 candle_count 개수만 반환
        valid_df = df.dropna(subset=['rsi']).tail(candle_count)
        
        # 필요한 열만 선택
        result_df = valid_df[['market', 'candle_date_time_utc', 'candle_date_time_kst', 'timestamp', 'close', 'rsi']]
        
        return result_df
    
    def calculate_stochastic(self, df=None, k_period=14, d_period=3, candle_count=100):
        """
        스토캐스틱 오실레이터(Stochastic Oscillator) 계산
        :param df: 사용할 DataFrame (default: None - 내부 데이터 사용)
        :param k_period: %K 계산 기간 (default: 14)
        :param d_period: %D 계산 기간 (default: 3)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :return: 스토캐스틱 값이 포함된 DataFrame
        """
        # DataFrame이 전달되지 않았다면 내부 데이터 사용
        if df is None:
            if self.df is None:
                self.logger.warning("데이터가 로드되지 않음. load_data() 먼저 호출 필요")
                return None
            df = self.df.copy()
        
        # 최고가, 최저가 계산 (k_period 기간 동안)
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        # %K 계산: (현재가 - 최저가) / (최고가 - 최저가) * 100
        df['k_value'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
        
        # %D 계산: %K의 d_period 이동평균
        df['d_value'] = df['k_value'].rolling(window=d_period).mean()
        
        # NaN 값 제거하고 최근 candle_count 개수만 반환
        valid_df = df.dropna(subset=['k_value', 'd_value']).tail(candle_count)
        
        # 필요한 열만 선택
        result_df = valid_df[['market', 'candle_date_time_utc', 'candle_date_time_kst', 'timestamp', 
                         'close', 'k_value', 'd_value']]
        
        return result_df
    
    def calculate_ema(self, df=None, period=20, candle_count=100):
        """
        지수이동평균(Exponential Moving Average) 계산
        :param df: 사용할 DataFrame (default: None - 내부 데이터 사용)
        :param period: EMA 계산 기간 (default: 20)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :return: EMA 값이 포함된 DataFrame
        """
        # DataFrame이 전달되지 않았다면 내부 데이터 사용
        if df is None:
            if self.df is None:
                self.logger.warning("데이터가 로드되지 않음. load_data() 먼저 호출 필요")
                return None
            df = self.df.copy()
        
        # EMA 계산 (pandas의 ewm 사용)
        # span=period는 EMA의 N+1 기간과 동일 (smoothing factor: 2/(N+1))
        df['ema'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # NaN 값 제거하고 최근 candle_count 개수만 반환
        valid_df = df.dropna(subset=['ema']).tail(candle_count)
        
        # 필요한 열만 선택
        result_df = valid_df[['market', 'candle_date_time_utc', 'candle_date_time_kst', 'timestamp', 'close', 'ema']]
        
        return result_df
    
    def calculate_bollinger_bands(self, df=None, period=20, deviation=2.0, candle_count=100):
        """
        볼린저 밴드(Bollinger Bands) 계산
        :param df: 사용할 DataFrame (default: None - 내부 데이터 사용)
        :param period: 이동평균 기간 (default: 20)
        :param deviation: 표준편차 승수 (default: 2.0)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :return: 볼린저 밴드 값이 포함된 DataFrame
        """
        # DataFrame이 전달되지 않았다면 내부 데이터 사용
        if df is None:
            if self.df is None:
                self.logger.warning("데이터가 로드되지 않음. load_data() 먼저 호출 필요")
                return None
            df = self.df.copy()
        
        # 중앙선 (단순이동평균)
        df['middle_band'] = df['close'].rolling(window=period).mean()
        
        # 표준편차 계산
        df['std'] = df['close'].rolling(window=period).std()
        
        # 상단선 = 중앙선 + 표준편차 * 승수
        df['upper_band'] = df['middle_band'] + (df['std'] * deviation)
        
        # 하단선 = 중앙선 - 표준편차 * 승수
        df['lower_band'] = df['middle_band'] - (df['std'] * deviation)
        
        # 밴드폭 = (상단선 - 하단선) / 중앙선
        df['bandwidth'] = (df['upper_band'] - df['lower_band']) / df['middle_band']
        
        # NaN 값 제거하고 최근 candle_count 개수만 반환
        valid_df = df.dropna(subset=['middle_band']).tail(candle_count)
        
        # 필요한 열만 선택
        result_df = valid_df[['market', 'candle_date_time_utc', 'candle_date_time_kst', 'timestamp',
                         'close', 'upper_band', 'middle_band', 'lower_band', 'bandwidth']]
        
        return result_df
    
    def calculate_macd(self, df=None, short_period=12, long_period=26, signal_period=9, candle_count=100):
        """
        MACD(Moving Average Convergence Divergence) 계산
        :param df: 사용할 DataFrame (default: None - 내부 데이터 사용)
        :param short_period: 단기 EMA 기간 (default: 12)
        :param long_period: 장기 EMA 기간 (default: 26)
        :param signal_period: 시그널 라인 기간 (default: 9)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :return: MACD 값이 포함된 DataFrame
        """
        # DataFrame이 전달되지 않았다면 내부 데이터 사용
        if df is None:
            if self.df is None:
                self.logger.warning("데이터가 로드되지 않음. load_data() 먼저 호출 필요")
                return None
            df = self.df.copy()
        
        # 단기 EMA
        df['ema_short'] = df['close'].ewm(span=short_period, adjust=False).mean()
        
        # 장기 EMA
        df['ema_long'] = df['close'].ewm(span=long_period, adjust=False).mean()
        
        # MACD 라인 = 단기 EMA - 장기 EMA
        df['macd_line'] = df['ema_short'] - df['ema_long']
        
        # 시그널 라인 = MACD의 EMA
        df['signal_line'] = df['macd_line'].ewm(span=signal_period, adjust=False).mean()
        
        # 히스토그램 = MACD 라인 - 시그널 라인
        df['histogram'] = df['macd_line'] - df['signal_line']
        
        # NaN 값 제거하고 최근 candle_count 개수만 반환
        valid_df = df.dropna(subset=['macd_line', 'signal_line']).tail(candle_count)
        
        # 필요한 열만 선택
        result_df = valid_df[['market', 'candle_date_time_utc', 'candle_date_time_kst', 'timestamp',
                         'close', 'macd_line', 'signal_line', 'histogram']]
        
        return result_df
    
    def calculate_ichimoku(self, df=None, tenkan_period=9, kijun_period=26, senkou_b_period=52, candle_count=100):
        """
        일목균형표(Ichimoku Kinko Hyo) 계산
        :param df: 사용할 DataFrame (default: None - 내부 데이터 사용)
        :param tenkan_period: 전환선 기간 (default: 9)
        :param kijun_period: 기준선 기간 (default: 26)
        :param senkou_b_period: 선행스팬B 기간 (default: 52)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :return: 일목균형표 값이 포함된 DataFrame
        """
        # DataFrame이 전달되지 않았다면 내부 데이터 사용
        if df is None:
            if self.df is None:
                self.logger.warning("데이터가 로드되지 않음. load_data() 먼저 호출 필요")
                return None
            df = self.df.copy()
        
        # 전환선(Tenkan-sen) = (n기간 최고가 + n기간 최저가) / 2
        high_tenkan = df['high'].rolling(window=tenkan_period).max()
        low_tenkan = df['low'].rolling(window=tenkan_period).min()
        df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2
        
        # 기준선(Kijun-sen) = (n기간 최고가 + n기간 최저가) / 2
        high_kijun = df['high'].rolling(window=kijun_period).max()
        low_kijun = df['low'].rolling(window=kijun_period).min()
        df['kijun_sen'] = (high_kijun + low_kijun) / 2
        
        # 선행스팬A(Senkou Span A) = (전환선 + 기준선) / 2, 26일 후에 그려짐
        df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(kijun_period)
        
        # 선행스팬B(Senkou Span B) = (n기간 최고가 + n기간 최저가) / 2, 26일 후에 그려짐
        high_senkou = df['high'].rolling(window=senkou_b_period).max()
        low_senkou = df['low'].rolling(window=senkou_b_period).min()
        df['senkou_span_b'] = ((high_senkou + low_senkou) / 2).shift(kijun_period)
        
        # 후행스팬(Chikou Span) = 현재 종가, 26일 전에 그려짐
        # pandas에서 shift(-n)은 n일 앞의 값을 가져옴(데이터를 과거로 이동)
        df['chikou_span'] = df['close'].shift(-kijun_period)
        
        # NaN 값 제거하고 최근 candle_count 개수만 반환
        # 후행스팬 때문에 미래 데이터가 필요하므로 shift(-kijun_period) 부분은 NaN이 발생
        # 실제 차트에서는 이 부분을 주의하여 표시해야 함
        valid_df = df.dropna(subset=['tenkan_sen', 'kijun_sen']).tail(candle_count)
        
        # 필요한 열만 선택
        result_df = valid_df[['market', 'candle_date_time_utc', 'candle_date_time_kst', 'timestamp', 'close',
                         'tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span']]
        
        return result_df
    
    def calculate_keltner_channel(self, df=None, ema_period=20, atr_period=10, multiplier=2.0, candle_count=100, use_wilder_atr=True):
        """
        켈트너 채널(Keltner Channel) 계산
        :param df: 사용할 DataFrame (default: None - 내부 데이터 사용)
        :param ema_period: EMA 기간 (default: 20)
        :param atr_period: ATR 기간 (default: 10)
        :param multiplier: ATR 승수 (default: 2.0)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :param use_wilder_atr: Wilder의 ATR 계산 방식 사용 여부 (default: True)
        :return: 켈트너 채널 값이 포함된 DataFrame
        """
        # DataFrame이 전달되지 않았다면 내부 데이터 사용
        if df is None:
            if self.df is None:
                self.logger.warning("데이터가 로드되지 않음. load_data() 먼저 호출 필요")
                return None
            df = self.df.copy()
        
        # True Range 계산
        df['h-l'] = df['high'] - df['low']
        df['h-pc'] = abs(df['high'] - df['close'].shift(1))
        df['l-pc'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        
        if use_wilder_atr:
            # Wilder's 평활화 방식의 ATR
            # 첫 번째 값은 단순 평균으로 계산
            df['atr'] = df['tr'].rolling(window=atr_period).mean()
            
            # 첫 번째 유효값부터 Wilder 방식 적용
            first_valid = df['atr'].first_valid_index()
            if first_valid is not None:
                for i in range(df.index.get_loc(first_valid) + 1, len(df)):
                    df.loc[df.index[i], 'atr'] = (df.loc[df.index[i-1], 'atr'] * (atr_period-1) + 
                                               df.loc[df.index[i], 'tr']) / atr_period
        else:
            # 단순이동평균 방식의 ATR
            df['atr'] = df['tr'].rolling(window=atr_period).mean()
        
        # 중앙선 (EMA)
        df['middle_channel'] = df['close'].ewm(span=ema_period, adjust=False).mean()
        
        # 상단선 = 중앙선 + ATR * multiplier
        df['upper_channel'] = df['middle_channel'] + (df['atr'] * multiplier)
        
        # 하단선 = 중앙선 - ATR * multiplier
        df['lower_channel'] = df['middle_channel'] - (df['atr'] * multiplier)
        
        # NaN 값 제거하고 최근 candle_count 개수만 반환
        valid_df = df.dropna(subset=['middle_channel', 'upper_channel', 'lower_channel']).tail(candle_count)
        
        # 필요한 열만 선택
        result_df = valid_df[['market', 'candle_date_time_utc', 'candle_date_time_kst', 'timestamp',
                         'close', 'middle_channel', 'upper_channel', 'lower_channel']]
        
        return result_df
    
    def calculate_vwap(self, df=None, period=20, candle_count=100):
        """
        거래량가중평균가격(VWAP, Volume Weighted Average Price) 계산
        :param df: 사용할 DataFrame (default: None - 내부 데이터 사용)
        :param period: 계산 기간 (default: 20)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :return: VWAP 값이 포함된 DataFrame
        """
        # DataFrame이 전달되지 않았다면 내부 데이터 사용
        if df is None:
            if self.df is None:
                self.logger.warning("데이터가 로드되지 않음. load_data() 먼저 호출 필요")
                return None
            df = self.df.copy()
        
        # 각 봉에 대한 가격 * 거래량 계산
        df['pv'] = ((df['high'] + df['low'] + df['close']) / 3) * df['volume']
        
        # 누적 가격 * 거래량 및 누적 거래량 계산 (기간 내)
        df['cum_pv'] = df['pv'].rolling(window=period).sum()
        df['cum_volume'] = df['volume'].rolling(window=period).sum()
        
        # VWAP 계산
        df['vwap'] = df['cum_pv'] / df['cum_volume']
        
        # NaN 값 제거하고 최근 candle_count 개수만 반환
        valid_df = df.dropna(subset=['vwap']).tail(candle_count)
        
        # 필요한 열만 선택
        result_df = valid_df[['market', 'candle_date_time_utc', 'candle_date_time_kst', 'timestamp', 'close', 'vwap']]
        
        return result_df
    
    def analyze_all(self, market=None, candle_count=100, max_period=500, params=None):
        """
        기술적 지표 분석 실행 - 한 번의 데이터 로드로 효율적으로 계산
        :param market: 분석 대상 마켓 코드 (default: None - 현재 설정된 market 사용)
        :param candle_count: 반환할 캔들 개수 (default: 100)
        :param max_period: 로드할 최대 캔들 개수 (default: 500)
        :param params: 계산할 지표 목록 (default: None - 모든 지표 계산)
                      예: ['rsi', 'macd', 'bollinger']
        :return: 분석 결과 Dictionary
        """
        if market is not None:
            self.market = market
        
        # 모든 지표 계산에 필요한 충분한 데이터를 한 번에 로드
        self.load_data(period=max_period)
        
        # 결과 저장용 딕셔너리
        results = {}
        
        # 지표 계산 함수 매핑
        indicator_map = {
            'rsi': lambda: self.calculate_rsi(df=self.df, period=14, candle_count=candle_count, use_wilder=True),
            'stochastic': lambda: self.calculate_stochastic(df=self.df, k_period=14, d_period=3, candle_count=candle_count),
            'ema_short': lambda: self.calculate_ema(df=self.df, period=9, candle_count=candle_count),
            'ema_medium': lambda: self.calculate_ema(df=self.df, period=20, candle_count=candle_count),
            'ema_long': lambda: self.calculate_ema(df=self.df, period=50, candle_count=candle_count),
            'bollinger': lambda: self.calculate_bollinger_bands(df=self.df, period=20, deviation=2.0, candle_count=candle_count),
            'macd': lambda: self.calculate_macd(df=self.df, short_period=12, long_period=26, signal_period=9, candle_count=candle_count),
            'ichimoku': lambda: self.calculate_ichimoku(df=self.df, tenkan_period=9, kijun_period=26, senkou_b_period=52, candle_count=candle_count),
            'keltner': lambda: self.calculate_keltner_channel(df=self.df, ema_period=20, atr_period=10, multiplier=2.0, candle_count=candle_count, use_wilder_atr=True),
            'vwap': lambda: self.calculate_vwap(df=self.df, period=20, candle_count=candle_count),
        }
        
        try:
            # 계산할 지표가 지정되지 않았으면 모든 지표 계산
            indicators_to_calculate = params if params else indicator_map.keys()
            
            for indicator in indicators_to_calculate:
                if indicator in indicator_map:
                    results[indicator] = indicator_map[indicator]()
                else:
                    self.logger.warning(f"알 수 없는 지표: {indicator}")
            
            self.logger.info(f"{self.market} 기술적 분석 완료: {len(results)}개 지표, {candle_count}개 캔들")
        except Exception as e:
            self.logger.error(f"{self.market} 기술적 분석 중 오류 발생: {str(e)}")
        
        return results
