# Django Quant Trader Backend

이 프로젝트는 양적 거래 플랫폼을 위한 백엔드 시스템입니다. Django로 구축되었으며 전략 실행 및 데이터 수집과 같은 비동기 작업을 처리하기 위해 Celery를 통합하고 있습니다.

## 프로젝트 구조

```
django_backend/
│
├── data_provider/         # DataProvider (주기적인 데이터 수집)
│   ├── migrations/
│   ├── tasks.py            # Celery task 정의
│   ├── services.py         # 데이터 수집 로직
│   ├── models.py           # 데이터 모델 정의
│   └── __init__.py
│
├── trader/                 # Trader
│   ├── migrations/
│   ├── services.py
│   └── __init__.py
│
├── strategy/               # Strategy (주기적으로 실행될 전략)
│   ├── migrations/
│   ├── tasks.py            # Celery task 정의
│   ├── services.py         # 전략 실행 로직
│   └── __init__.py
│
├──  analyzer/               # Analyzer
│   ├── migrations/
│   ├──services.py
│   └──  __init__.py
│
├── operator/                   # Operation layer (중재 역할)
│   ├── operator.py
│   └── tasks.py                # Celery로 처리되는 중재 작업들
│
├── controller/                 # Controller layer
│   ├── kakao_controller/    # KakaoTalk Controller
│   │   ├── kakao_controller.py
│   │   └── __init__.py
│   │
│   ├── simulator/              # Simulator
│   │   ├── simulator.py
│   │   └── __init__.py
│   │
│   ├── controller/             # Main controller
│   │   ├── controller.py
│   │   └── __init__.py
│   │
│   └── jpt_controller/         # JptController
│       ├── jpt_controller.py
│       └── __init__.py
│
├── config/                     # Django 설정 및 Celery 설정
│   ├── celery.py               # Celery 설정 파일
│   ├── settings.py             # Django 설정 파일 (Celery 관련 설정 포함)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── manage.py                   # Django 관리 스크립트
├── celerybeat-schedule         # Celery beat 스케줄러 파일 (주기적 작업)
├── requirements.txt            # 프로젝트의 패키지 종속성 리스트 (Celery 포함)
├── environment.yml             # Conda 환경 설정 파일
├── environment-windows.yml     # Windows 특정 환경 설정
├── environment-macos.yml       # macOS 특정 환경 설정
└── setup_environment.py        # 환경 설정 스크립트
```

## 시작하기

이 프로젝트를 설정하고 실행하려면 다음 단계를 따르세요:

### Prerequisites

- Python 3.9+
- Conda (Anaconda)
- Redis (Celery 브로커용)
- SQLite (또는 선호하는 데이터베이스)

### Installation

1. Clone the repository:

   ```bash
   git clone https://your-repo-url.git
   cd django-quant-trader
   ```

2. Conda 환경 설정:

   ```bash
   python setup_environment.py
   ```

   이 스크립트는 Windows와 macOS 모두에 필요한 모든 종속성을 가진 Conda 환경을 생성합니다.

3. Conda 환경 활성화:

   ```bash
   conda activate django-quant-trader
   ```

4. 데이터베이스 마이그레이션 적용:

   ```bash
   python manage.py migrate
   ```

5. 슈퍼유저 생성 (선택사항):
   ```bash
   python manage.py createsuperuser
   ```

### 애플리케이션 실행

1. Django 개발 서버 시작:

   ```bash
   python manage.py runserver
   ```

2. Celery 워커 시작:

   ```bash
   celery -A config worker --loglevel=info
   ```

3. 주기적 작업을 위한 Celery beat 시작:
   ```bash
   celery -A config beat --loglevel=info
   ```

## 개발

다양한 플랫폼(Windows 및 macOS)에서의 개발을 위해 프로젝트는 별도의 환경 파일을 사용합니다:

- `environment.yml`: 모든 플랫폼에 공통된 종속성
- `environment-windows.yml`: Windows 특정 종속성
- `environment-macos.yml`: macOS 특정 종속성

`setup_environment.py` 스크립트는 운영 체제를 자동으로 감지하고 적절한 환경을 설정합니다.

## 진행 목표

1. 매수 매도 시스템 구축
2. 매수 매도 시스템 테스트
3. log 시스템 구축
4. 전략 구축

- EMA, RSI, MACD 등의 지표를 사용하여 전략 구축
- DeepAR 모델을 사용하여 전략 구축
- 두 전략 스태킹 모델을 사용하여 전략 구축
- (추후) ETH 와 같은 경우 커플링 매매 전략 구축

5. 전략 테스트
6. 매매 시스템 구축
7. 매매 시스템 테스트
8. 매매 시스템 운용
9. KakoTalk Controller 구축

10. AWS 배포
11. Jenkins 연동 CI/CD
12. 모니터링 시스템 구축

## 수정 사항

- db sqlite 3 -> postgresql 변경

  이유 : 분봉데이터가 너무 커서 조회에 어려움이 있어서 파티셔닝을 적용해 저장하기 위해서

## 추후 생각해봐야할 문제

- 상태관리 (Redis 상에서 상태관리를 fetch_historical_upbit_data 에서만 하고 있는 부분 고려)
- upbit 데이터 db에 동시에 삽입 혹은 수정할 경우 충돌 가능성 체크

## 어려웠던 부분

- django 쿼리 최적화 ex) lazy-loading 문제
- upbit api상 데이터가 없는부분 존재 -> 빈시간을 제외한 분봉데이터를 return 하여 db데이터 중복 오류 (요청시간대와 return 데이터 시간대가 일치하지 않을때 null 값 저장으로 임시조치)
