# django_backend/config/celery.py
import os
from celery import Celery
from celery.signals import worker_ready
from django.conf import settings

# Django 설정 모듈을 Celery의 기본으로 사용
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_backend.config.settings')

app = Celery('django_backend')

# 문자열로 등록한 이유는 Celery Worker가 자식 프로세스에게 전달할 때 pickle로 직렬화하는데 문제가 있을 수 있다.
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 장고 앱 설정에서 task를 불러온다.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

@worker_ready.connect
def at_start(sender, **kwargs):
    print("Celery worker is ready.")
    with sender.app.connection() as conn:
        sender.app.send_task('data_provider.tasks.fetch_missing_upbit_data', 
                             connection=conn)