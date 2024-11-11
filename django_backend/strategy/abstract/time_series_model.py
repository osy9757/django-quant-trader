from abc import ABC, abstractmethod

class TimeSeriesModel(ABC):
    """시계열 데이터 예측 모델을 위한 추상 클래스"""

    @abstractmethod
    def preprocess_data(self, data):
        """예측에 필요한 데이터 전처리"""
        pass

    @abstractmethod
    def initialize_model(self):
        """모델 초기화 설정"""
        pass

    @abstractmethod
    def predict(self, data):
        """데이터에 대한 예측 수행"""
        pass

    @abstractmethod
    def postprocess_results(self, results):
        """예측 결과 후처리"""
        pass

    @abstractmethod
    def interpret_results(self, results):
        """예측 결과를 매매 신호 등으로 해석"""
        pass
