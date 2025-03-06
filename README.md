# Django Quant Trader Backend

이 프로젝트는 양적 거래 플랫폼을 위한 백엔드 시스템입니다. Django로 구축되었으며 전략 실행 및 데이터 수집과 같은 비동기 작업을 처리하기 위해 Celery를 통합하고 있습니다.

## 프로젝트 구조

```
django_backend/
│
├── data_provider/         # DataProvider (주기적인 데이터 수집을 담당)
│   ├── migrations/        # 데이터베이스 마이그레이션 파일
│   ├── tasks.py           # Celery 작업 정의 파일
│   ├── services.py        # 데이터 수집 로직
│   ├── models.py          # 데이터베이스 모델 정의
│   └── __init__.py
│
├── trader/                 # Trader (매수/매도 작업 수행)
│   ├── migrations/        # 데이터베이스 마이그레이션 파일
│   ├── services.py        # 거래 로직 구현
│   └── __init__.py
│
├── strategy/               # Strategy (주기적으로 실행될 전략 관리)
│   ├── migrations/        # 데이터베이스 마이그레이션 파일
│   ├── tasks.py           # Celery 작업 정의 파일
│   ├── services.py        # 전략 실행 로직
│   ├── strategies/        # 다양한 전략 구현 디렉토리
│   └── __init__.py
│
├── analyzer/               # Analyzer (데이터 분석을 수행)
│   ├── migrations/        # 데이터베이스 마이그레이션 파일
│   ├── services.py        # 분석 로직 구현
│   └── __init__.py
│
├── operator/               # Operator (중재 역할을 수행)
│   ├── operator.py        # 중재 기능 정의
│   └── tasks.py           # Celery로 처리되는 중재 작업
│
├── controller/             # Controller layer (외부 요청 처리)
│   ├── kakao_controller/   # KakaoTalk 연동 컨트롤러
│   │   ├── kakao_controller.py
│   │   └── __init__.py
│   │
│   ├── simulator/          # Simulator (시뮬레이션 기능)
│   │   ├── simulator.py
│   │   └── __init__.py
│   │
│   ├── controller/         # Main controller (중앙 컨트롤러)
│   │   ├── controller.py
│   │   └── __init__.py
│   │
│   └── jpt_controller/     # Jpt 연동 컨트롤러
│       ├── jpt_controller.py
│       └── __init__.py
│
├── config/                 # Django 및 Celery 설정
│   ├── celery.py           # Celery 설정 파일
│   ├── settings.py         # Django 설정 파일
│   ├── urls.py             # URL 설정
│   ├── wsgi.py             # WSGI 설정 (서버 실행)
│   └── asgi.py             # ASGI 설정 (비동기 서버 실행)
│
├── manage.py               # Django 관리 스크립트
├── celerybeat-schedule     # Celery beat 스케줄러 파일 (주기적 작업)
├── requirements.txt        # 패키지 종속성 리스트 (Celery 포함)
├── environment.yml         # Conda 환경 설정 파일
├── environment-windows.yml # Windows 환경 설정 파일
├── environment-macos.yml   # macOS 환경 설정 파일
└── setup_environment.py    # 환경 설정 스크립트
```

## 로직 흐름도
```
DataProvider (데이터 수집)
 │
 └─▶ Analyzer (기술적 분석 수행)
       ├─▶ MA, RSI, MACD, Bollinger 등 지표계산
       └─▶ 분석된 데이터(DB/Redis 저장)
                 │
                 └─▶ Strategy (기술적 분석 기반 1차 판단)
                       └─▶ 각 지표에 가중치를 적용해 판단
                             ├─▶ 결과: "매수 / 매도 / 유지"
                             └─▶ 결과(DB/Redis 저장)
                                       │
                                       └─▶ Operator (최종결정)
                                            │
                          ┌───────────┬───────────┐
                       매수/매도일때만 진행        유지면 더 이상 진행 X
                          │ AI 분석 추가
                          │
                          └─▶ AI Analyzer (가격 예측 및 신뢰도 분석)
                                    ├─▶ 상승/하락 확률 등 결과 제공
                                    └─▶ 결과(Operator 전달)
                                               │
                                               └─▶ Operator (AI 분석 결과로 최종 검토)
                                                       └─▶ Trader (실제 매수·매도)

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

2.

3. Celery 워커 시작:

   ```bash
   celery -A config worker --loglevel=info
   ```

4. 주기적 작업을 위한 Celery beat 시작:
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

- db 데이터 처리 방식

datetime 데이터 형식에서 처리
이유 : 기존에 에러 처리시 로그 기록을 편하게 하기 위해서 kst 데이터 타입으로 변경 후 처리 했으나 특정 시간대에 문제가 많이 발생하여 수정

## 추후 생각해봐야할 문제

- 상태관리 (Redis 상에서 상태관리를 fetch_historical_upbit_data 에서만 하고 있는 부분 고려)
- upbit 데이터 db에 동시에 삽입 혹은 수정할 경우 충돌 가능성 체크

## 어려웠던 부분

- django 쿼리 최적화 ex) lazy-loading 문제
- upbit api상 데이터가 없는부분 존재 -> 빈시간을 제외한 분봉데이터를 return 하여 db데이터 중복 오류 (요청시간대와 return 데이터 시간대가 일치하지 않을때 null 값 저장으로 임시조치)

## 잡설

- 트럼프, 일론머스크 트위터 NLP를 추가해야하나...
