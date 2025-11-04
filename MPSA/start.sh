#!/bin/bash
# ===================================
# MPSA 图像识别项目 - 容器内启动脚本
# 功能：接收参数并执行训练或推理
# ===================================
# 
# 参数说明：
#   $1: 运行模式 (train/inference)
#   $2: 数据集名称 (webfg400/webinat5000)
#
# 示例：
#   bash start.sh train webinat5000
#   bash start.sh inference webfg400
# ===================================

set -e  # 遇到错误立即退出

# ===================================
# 第一步：解析参数
# ===================================
MODE=$1
DATASET=$2

echo "=========================================="
echo "MPSA 图像识别项目 - Docker容器"
echo "=========================================="
echo "运行模式: $MODE"
echo "数据集: $DATASET"
echo "=========================================="

# 验证参数
if [[ "$MODE" != "train" && "$MODE" != "inference" ]]; then
    echo "❌ 错误：运行模式必须是 'train' 或 'inference'"
    echo "用法: bash start.sh <train|inference> <webfg400|webinat5000>"
    exit 1
fi

if [[ "$DATASET" != "webfg400" && "$DATASET" != "webinat5000" ]]; then
    echo "❌ 错误：数据集必须是 'webfg400' 或 'webinat5000'"
    echo "用法: bash start.sh <train|inference> <webfg400|webinat5000>"
    exit 1
fi

# ===================================
# 第二步：设置配置文件
# ===================================
# 根据数据集选择对应的配置文件
if [[ "$DATASET" == "webfg400" ]]; then
    CONFIG_FILE="/app/configs/swin-webfg400.yaml"
    CONFIG_NAME="swin-webfg400.yaml"
    echo "📝 使用配置文件: swin-webfg400.yaml (Docker版)"
elif [[ "$DATASET" == "webinat5000" ]]; then
    CONFIG_FILE="/app/configs/swin-webinat5000.yaml"
    CONFIG_NAME="swin-webinat5000.yaml"
    echo "📝 使用配置文件: swin-webinat5000.yaml (Docker版)"
fi

# 验证配置文件是否存在
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ 错误：配置文件不存在: $CONFIG_FILE"
    exit 1
fi

# ===================================
# 第三步：修改setup.py中的配置文件路径
# ===================================
# 临时修改setup.py以使用正确的配置文件
echo "🔧 配置项目参数..."

# 备份原始setup.py
cp /app/setup.py /app/setup.py.bak

# 修改配置文件路径（修改setup.py的第9行）
sed -i "9s|.*|cfg_file = os.path.join('configs', '$CONFIG_NAME')  # Docker: 自动设置|" /app/setup.py

# 注释掉模型路径配置（Docker中不需要恢复checkpoint）
sed -i '31,39s/^/# /' /app/setup.py

# ===================================
# 第四步：设置推理模式（如果需要）
# ===================================
# 临时修改配置文件的推理模式设置
CONFIG_TEMP="/tmp/config_temp.yaml"
cp "$CONFIG_FILE" "$CONFIG_TEMP"

if [[ "$MODE" == "inference" ]]; then
    echo "🔮 设置为推理模式..."
    # 将inference_mode设置为True
    sed -i 's/inference_mode: False/inference_mode: True/g' "$CONFIG_TEMP"
    sed -i 's/inference_mode: false/inference_mode: True/g' "$CONFIG_TEMP"
    # 复制回原位置
    cp "$CONFIG_TEMP" "$CONFIG_FILE"
else
    echo "🏋️  设置为训练模式..."
    # 将inference_mode设置为False
    sed -i 's/inference_mode: True/inference_mode: False/g' "$CONFIG_TEMP"
    sed -i 's/inference_mode: true/inference_mode: False/g' "$CONFIG_TEMP"
    # 复制回原位置
    cp "$CONFIG_TEMP" "$CONFIG_FILE"
fi

# ===================================
# 第五步：检查数据集是否挂载
# ===================================
echo "📂 检查数据集挂载..."

if [[ "$DATASET" == "webfg400" ]]; then
    DATA_DIR="/data/webfg400_train"
    TEST_DIR="/data/webfg400_test_B"  # B榜测试集
else
    DATA_DIR="/data/webinat5000_train"
    TEST_DIR="/data/webinat5000_test_B"  # B榜测试集
fi

if [[ ! -d "$DATA_DIR" ]]; then
    echo "⚠️  警告：训练数据目录不存在: $DATA_DIR"
    echo "请确保在运行docker时正确挂载了数据集目录"
fi

if [[ "$MODE" == "inference" && ! -d "$TEST_DIR" ]]; then
    echo "⚠️  警告：测试数据目录不存在: $TEST_DIR"
    echo "请确保在运行docker时正确挂载了测试集目录"
fi

# ===================================
# 第六步：检查预训练模型
# ===================================
echo "🤖 检查预训练模型..."

# 两个数据集共用同一个预训练模型
PRETRAINED_MODEL="/app/pretrained/swin_base_patch4_window12_384.pth"

if [[ -f "$PRETRAINED_MODEL" ]]; then
    echo "✅ 预训练模型存在: $(basename "$PRETRAINED_MODEL")"
else
    echo "⚠️  警告：预训练模型不存在: $PRETRAINED_MODEL"
fi

# ===================================
# 第七步：创建输出目录
# ===================================
echo "📁 准备输出目录..."
mkdir -p /outputs
mkdir -p /app/output

# ===================================
# 第八步：运行主程序
# ===================================
echo "=========================================="
echo "🚀 开始执行 $MODE 任务..."
echo "=========================================="

cd /app

# 运行主程序
if [[ "$MODE" == "train" ]]; then
    echo "📊 开始训练 $DATASET 数据集..."
    python -u main.py 2>&1 | tee /outputs/training_${DATASET}_$(date +%Y%m%d_%H%M%S).log
    
    echo ""
    echo "=========================================="
    echo "✅ 训练完成！"
    echo "=========================================="
    echo "📁 输出文件位置："
    echo "   - 模型权重: /app/output/${DATASET}/"
    echo "   - 训练日志: /outputs/training_${DATASET}_*.log"
    echo "=========================================="
    
else  # inference mode
    echo "🔮 开始推理 $DATASET 数据集..."
    python -u main.py 2>&1 | tee /outputs/inference_${DATASET}_$(date +%Y%m%d_%H%M%S).log
    
    echo ""
    echo "=========================================="
    echo "✅ 推理完成！"
    echo "=========================================="
    echo "📁 输出文件位置："
    echo "   - 预测结果: /app/output/${DATASET}/*/pred_results_*.csv"
    echo "   - 推理日志: /outputs/inference_${DATASET}_*.log"
    echo "=========================================="
    
    # 复制预测结果到输出目录
    echo "📋 复制预测结果到 /outputs/ ..."
    find /app/output/${DATASET}/ -name "pred_results_*.csv" -exec cp {} /outputs/ \; 2>/dev/null || true
fi

# ===================================
# 第九步：恢复原始配置
# ===================================
echo "🔄 恢复原始配置..."
mv /app/setup.py.bak /app/setup.py

echo ""
echo "=========================================="
echo "✅ 所有任务完成！"
echo "=========================================="

