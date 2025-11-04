# ===================================
# MPSA 图像识别项目 - Docker镜像
# 支持训练和推理模式
# 支持数据集：WebFG-400 和 WebiNat-5000
# ===================================

# 基础镜像：PyTorch 2.0.0 + CUDA 11.8
FROM pytorch/pytorch:2.0.0-cuda11.8-cudnn8-runtime

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    wget \
    vim \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（使用Docker专用的精简版）
COPY requirements_docker.txt /app/requirements_docker.txt

# 安装Python依赖
# 注意：PyTorch 2.0.0已包含在基础镜像中
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements_docker.txt

# 复制预训练模型（两个数据集共用同一个模型）
RUN mkdir -p /app/pretrained
COPY pretrained/swin_base_patch4_window12_384.pth /app/pretrained/swin_base_patch4_window12_384.pth

# 复制项目代码
COPY models/ /app/models/
COPY utils/ /app/utils/
COPY settings/ /app/settings/
COPY visualize/ /app/visualize/
COPY main.py /app/main.py
COPY setup.py /app/setup.py
# README.md是项目原始说明，不打包进镜像
# COPY README.md /app/README.md

# 复制配置文件（Docker专用版本）
# 注意：构建时需要使用MPSA目录作为context
COPY configs/swin-webfg400-docker.yaml /app/configs/swin-webfg400.yaml
COPY configs/swin-webinat5000-docker.yaml /app/configs/swin-webinat5000.yaml

# 复制容器内启动脚本
# 注意：start.sh需要存在于MPSA目录（构建上下文）
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# 创建输出目录
RUN mkdir -p /app/output

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:$PATH
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# 默认工作目录
WORKDIR /app

# 容器启动时执行的脚本
ENTRYPOINT ["/bin/bash", "/app/start.sh"]

