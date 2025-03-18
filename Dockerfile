FROM public.ecr.aws/lambda/python:3.12

# 작업 디렉토리 복사
COPY . ${LAMBDA_TASK_ROOT}

# 필요한 도구 설치 및 ffmpeg 설치
RUN dnf install -y wget tar xz && \
    cd /tmp && \
    rm -rf /usr/local/bin/ffmpeg && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xf ffmpeg-release-amd64-static.tar.xz && \
    cp ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ && \
    cp ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg-*-amd64-static* && \
    chmod 755 /usr/local/bin/ffmpeg && \
    chmod 755 /usr/local/bin/ffprobe

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# Lambda 핸들러 설정
CMD ["lambda_function.lambda_handler"]
