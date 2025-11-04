#!/bin/bash
# ===================================
# MPSA 图像识别项目 - 宿主机启动脚本
# 功能：交互式选择运行模式和数据集，自动启动Docker容器
# ===================================
#
# 使用方法：
#   bash run.sh
#
# 支持的运行模式：
#   - train: 训练模式
#   - inference: 推理模式
#
# 支持的数据集：
#   - webfg400: WebFG-400 (400类)
#   - webinat5000: WebiNat-5000 (5000类)
# ===================================

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Docker镜像名称
IMAGE_NAME="mpsa-image:v1.0"

echo ""
echo "=========================================="
echo "     MPSA 图像识别项目 - Docker启动脚本"
echo "=========================================="
echo ""

# ===================================
# 第一步：选择运行模式
# ===================================
echo -e "${BLUE}[步骤 1/3]${NC} 请选择运行模式："
echo "  1. 训练模式 (train)"
echo "  2. 推理模式 (inference)"
echo ""
read -p "请输入选项 [1/2]: " mode_choice

case $mode_choice in
    1)
        MODE="train"
        echo -e "${GREEN}✓${NC} 已选择：训练模式 (train)"
        ;;
    2)
        MODE="inference"
        echo -e "${GREEN}✓${NC} 已选择：推理模式 (inference)"
        ;;
    *)
        echo -e "${RED}✗${NC} 错误：无效的选项"
        exit 1
        ;;
esac

echo ""

# ===================================
# 第二步：选择数据集
# ===================================
echo -e "${BLUE}[步骤 2/3]${NC} 请选择数据集："
echo "  1. WebFG-400 (400类)"
echo "  2. WebiNat-5000 (5000类)"
echo ""
read -p "请输入选项 [1/2]: " data_choice

case $data_choice in
    1)
        DATASET="webfg400"
        echo -e "${GREEN}✓${NC} 已选择：WebFG-400 数据集"
        ;;
    2)
        DATASET="webinat5000"
        echo -e "${GREEN}✓${NC} 已选择：WebiNat-5000 数据集"
        ;;
    *)
        echo -e "${RED}✗${NC} 错误：无效的选项"
        exit 1
        ;;
esac

echo ""

# ===================================
# 第三步：输入数据集路径
# ===================================
echo -e "${BLUE}[步骤 3/3]${NC} 请输入宿主机数据集根目录路径"
echo ""
echo -e "${YELLOW}说明：${NC}"
echo "  数据集应包含以下子目录："
if [[ "$DATASET" == "webfg400" ]]; then
    echo "    - webfg400_train/train/  (训练集)"
    echo "    - webfg400_test_B/test_B/  (B榜测试集)"
else
    echo "    - webinat5000_train/train/  (训练集)"
    echo "    - webinat5000_test_B/test_B/  (B榜测试集)"
fi
echo ""
echo -e "${YELLOW}示例：${NC}/root/autodl-tmp/database"
echo ""
read -p "数据集路径: " host_data_path

# 去除路径末尾的斜杠
host_data_path="${host_data_path%/}"

# 验证路径是否存在
if [[ ! -d "$host_data_path" ]]; then
    echo -e "${RED}✗${NC} 错误：路径不存在: $host_data_path"
    exit 1
fi

# 验证数据集子目录是否存在
if [[ "$DATASET" == "webfg400" ]]; then
    TRAIN_DIR="$host_data_path/webfg400_train"
else
    TRAIN_DIR="$host_data_path/webinat5000_train"
fi

if [[ ! -d "$TRAIN_DIR" ]]; then
    echo -e "${YELLOW}⚠${NC}  警告：训练集目录不存在: $TRAIN_DIR"
    read -p "是否继续？[y/N]: " continue_choice
    if [[ "$continue_choice" != "y" && "$continue_choice" != "Y" ]]; then
        echo "已取消"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} 数据集路径验证通过"
fi

echo ""

# ===================================
# 第四步：设置输出目录
# ===================================
# 在当前目录创建outputs目录
OUTPUT_DIR="$(pwd)/outputs"
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}✓${NC} 输出目录已创建: $OUTPUT_DIR"

echo ""

# ===================================
# 第五步：显示配置总结
# ===================================
echo "=========================================="
echo -e "${BLUE}即将执行以下操作：${NC}"
echo "=========================================="
echo "  - 运行模式: $MODE"
echo "  - 数据集: $DATASET"
echo "  - 数据路径: $host_data_path"
echo "  - 输出路径: $OUTPUT_DIR"
echo "  - Docker镜像: $IMAGE_NAME"
echo "=========================================="
echo ""
read -p "确认启动容器？[Y/n]: " confirm
if [[ "$confirm" == "n" || "$confirm" == "N" ]]; then
    echo "已取消"
    exit 0
fi

echo ""

# ===================================
# 第六步：检查Docker镜像是否存在
# ===================================
echo "🐳 检查Docker镜像..."
if ! docker image inspect "$IMAGE_NAME" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠${NC}  镜像不存在: $IMAGE_NAME"
    echo ""
    echo "请先构建Docker镜像："
    echo "  cd /root/autodl-tmp/Docker"
    echo "  docker build -f Dockerfile -t $IMAGE_NAME /root/autodl-tmp/MPSA"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker镜像已就绪"

echo ""

# ===================================
# 第七步：启动Docker容器
# ===================================
echo "=========================================="
echo "🚀 正在启动Docker容器..."
echo "=========================================="
echo ""

# 构建docker run命令
# 说明：
#   --rm: 容器退出后自动删除
#   --gpus all: 使用所有GPU
#   -v: 挂载卷
#     - 数据集目录挂载为只读 (ro)
#     - 输出目录挂载为可读写
#   --shm-size: 共享内存大小（DataLoader需要）
#   --ipc=host: 使用宿主机IPC命名空间（避免共享内存问题）
#   $IMAGE_NAME: Docker镜像名称
#   $MODE $DATASET: 传递给容器内start.sh的参数

docker run --rm \
    --gpus all \
    -v "$host_data_path":/data:ro \
    -v "$OUTPUT_DIR":/outputs \
    --shm-size=16g \
    --ipc=host \
    "$IMAGE_NAME" \
    "$MODE" "$DATASET"

# 获取容器退出状态
EXIT_CODE=$?

echo ""
echo "=========================================="
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}✅ 容器执行成功！${NC}"
    echo "=========================================="
    echo ""
    echo "📁 输出文件位置："
    echo "   $OUTPUT_DIR"
    echo ""
    
    # 列出输出文件
    if [[ "$MODE" == "inference" ]]; then
        echo "📋 预测结果文件："
        find "$OUTPUT_DIR" -name "pred_results_*.csv" -type f 2>/dev/null | while read file; do
            echo "   - $(basename "$file")"
        done
    else
        echo "📊 训练输出文件："
        ls -lh "$OUTPUT_DIR" | tail -n +2
    fi
else
    echo -e "${RED}✗ 容器执行失败 (退出码: $EXIT_CODE)${NC}"
    echo "=========================================="
    echo ""
    echo "请查看输出日志以了解错误详情"
fi

echo ""
echo "=========================================="

