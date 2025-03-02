# Dockerfile
FROM continuumio/miniconda3:latest

# 작업 디렉터리를 /app으로 설정
WORKDIR /app

# 환경 파일 복사 및 conda 환경 생성
COPY environment.yml .
RUN conda env create -f environment.yml

# bash를 로그인 쉘처럼 사용하도록 초기화
SHELL ["/bin/bash", "-c"]
RUN conda init bash && echo "source activate django-quant-trader" >> /root/.bashrc

# 전체 소스코드 복사 (저장소 루트의 모든 파일이 /app에 복사됨)
COPY . .

# 기본 CMD (docker-compose에서 command 재정의 가능)
CMD ["bash"]
