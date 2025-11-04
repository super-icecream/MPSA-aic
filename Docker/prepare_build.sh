#!/bin/bash
# ===========================================
# Docker构建前准备脚本
# 功能：自动准备构建所需的文件
# ===========================================

echo "=== Docker构建前准备 ==="
echo ""

# 1. 复制start.sh
echo "[1/3] 复制start.sh到MPSA目录..."
cp /root/autodl-tmp/Docker/start.sh /root/autodl-tmp/MPSA/
chmod +x /root/autodl-tmp/MPSA/start.sh
echo "✅ start.sh已就绪"

# 2. 检查配置文件
echo "[2/3] 检查Docker配置文件..."
if [[ -f "/root/autodl-tmp/MPSA/configs/swin-webfg400-docker.yaml" ]] && \
   [[ -f "/root/autodl-tmp/MPSA/configs/swin-webinat5000-docker.yaml" ]]; then
    echo "✅ Docker配置文件已就绪"
else
    echo "⚠️  警告：Docker配置文件不完整"
    exit 1
fi

# 3. 检查预训练模型
echo "[3/3] 检查预训练模型..."
if [[ -f "/root/autodl-tmp/MPSA/pretrained/swin_base_patch4_window12_384.pth" ]]; then
    echo "✅ 预训练模型已就绪 ($(ls -lh /root/autodl-tmp/MPSA/pretrained/swin_base_patch4_window12_384.pth | awk '{print $5}'))"
else
    echo "⚠️  警告：预训练模型不存在"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ 所有准备工作完成！"
echo "=========================================="
echo ""
echo "现在可以构建Docker镜像："
echo "  cd /root/autodl-tmp/Docker"
echo "  docker build -f Dockerfile -t mpsa-image:v1.0 /root/autodl-tmp/MPSA"
echo ""

