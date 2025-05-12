# CUDA 11.8, cuDNN 8, Ubuntu 20.04
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu20.04

# 비대화 설치 모드
ENV DEBIAN_FRONTEND=noninteractive

# 필수 패키지 설치 (Python 3.8 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.8 python3-pip python3.8-dev \
    build-essential git curl wget ca-certificates \
    libgl1-mesa-glx libgl1-mesa-dri libglu1-mesa \
    libx11-6 libxcursor1 libxrandr2 libxss1 libvulkan1 \
    libxi6 libxcomposite1 libxdamage1 libxtst6 \
    xvfb freeglut3-dev libsm6 libxext6 libxrender-dev \
    libfontconfig1 libfontconfig1-dev \
    libfreetype6 libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# python, pip 기본 경로 연결
RUN ln -sf /usr/bin/python3.8 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip && \
    pip install --upgrade pip

# 사용자 추가
RUN useradd -ms /bin/bash developer
USER developer
WORKDIR /home/developer/api

# PYTHONPATH 설정
# ENV PYTHONPATH=/home/developer/semantic-kitti-api
ENV PYTHONPATH=/home/developer/api

# CUDA 호환 PyTorch GPU 버전 설치
RUN pip install --no-cache-dir \
    torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 기타 시각화 및 유틸 패키지 설치
RUN pip install \
    numpy==1.24.3 \
    matplotlib==3.7.1 \
    vispy==0.11.0 \
    opencv-python \
    PyYAML==6.0 \
    imgui[glfw]==1.4.0 \
    glfw==2.5.3 \
    PyOpenGL==3.1.6

# Qt X11 shared memory 버그 방지
ENV QT_X11_NO_MITSHM=1
ENV DISPLAY=:0

CMD ["/bin/bash"]