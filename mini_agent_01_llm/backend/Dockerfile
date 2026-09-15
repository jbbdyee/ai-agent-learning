FROM python:3.11-slim

WORKDIR /app

# 필요한 패키지 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 전체 파일 복사
COPY . .

# 백엔드 포트 노출
EXPOSE 8000

# uvicorn 서버 실행 (main.py의 app 기준, 만약 다른 파일명이라면 수정)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]