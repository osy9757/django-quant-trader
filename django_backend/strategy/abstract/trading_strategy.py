from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    """다양한 전략에 범용적으로 사용할 추상 클래스"""

    @abstractmethod
    def initialize_strategy(self):
        """전략 초기화 설정"""
        pass

    @abstractmethod
    def prepare_data(self, data):
        """전략 실행에 필요한 데이터 준비"""
        pass

    @abstractmethod
    def evaluate_conditions(self, data):
        """전략 조건을 평가"""
        pass

    @abstractmethod
    def generate_signals(self, data):
        """매매 신호를 생성"""
        pass

    @abstractmethod
    def interpret_signals(self, signals):
        """신호를 해석하여 의미 있는 정보로 변환"""
        pass
