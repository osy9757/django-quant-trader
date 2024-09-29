import os
import platform
import subprocess

def setup_environment():
    # 기본 환경 파일 설치
    subprocess.run(["conda", "env", "create", "-f", "environment.yml"])
    
    # 운영 체제 확인
    os_name = platform.system().lower()
    
    if os_name == "windows":
        # Windows 특정 패키지 설치
        subprocess.run(["conda", "env", "update", "-n", "django-quant-trader", "-f", "environment-windows.yml"])
    elif os_name == "darwin":  # macOS
        # macOS 특정 패키지 설치
        subprocess.run(["conda", "env", "update", "-n", "django-quant-trader", "-f", "environment-macos.yml"])
    
    print(f"Environment setup completed for {os_name}")

if __name__ == "__main__":
    setup_environment()
