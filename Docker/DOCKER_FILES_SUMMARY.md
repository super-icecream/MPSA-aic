# Docker化文件清单

## ✅ 已创建的文件

本文档列出了为Docker化MPSA项目创建的所有文件。

**📁 Docker文件位置**: `/root/autodl-tmp/Docker/`（已从MPSA目录移出）

### 📦 核心Docker文件

| 文件 | 位置 | 说明 | 状态 |
|------|------|------|------|
| **Dockerfile** | `/root/autodl-tmp/Docker/Dockerfile` | Docker镜像构建配置 | ✅ 已创建 |
| **.dockerignore** | `/root/autodl-tmp/Docker/.dockerignore` | 忽略不必要的文件 | ✅ 已创建 |
| **requirements_docker.txt** | `/root/autodl-tmp/Docker/requirements_docker.txt` | 精简版依赖清单 | ✅ 已创建 |
| **BUILD.md** | `/root/autodl-tmp/Docker/BUILD.md` | 构建说明文档 | ✅ 已创建 |

### 🔧 启动脚本

| 文件 | 位置 | 说明 | 状态 |
|------|------|------|------|
| **run.sh** | `/root/autodl-tmp/Docker/run.sh` | 宿主机交互式启动脚本 | ✅ 已创建 |
| **start.sh** | `/root/autodl-tmp/Docker/start.sh` | 容器内执行脚本 | ✅ 已创建 |

### ⚙️ Docker专用配置文件

| 文件 | 位置 | 说明 | 状态 |
|------|------|------|------|
| **swin-webfg400-docker.yaml** | `/root/autodl-tmp/MPSA/configs/`（源文件） | WebFG-400 Docker配置 | ✅ 已创建 |
| **swin-webinat5000-docker.yaml** | `/root/autodl-tmp/MPSA/configs/`（源文件） | WebiNat-5000 Docker配置 | ✅ 已创建 |
| **配置文件副本** | `/root/autodl-tmp/Docker/configs/`（备份） | 两个配置文件的副本 | ✅ 已备份 |

### 📖 文档

| 文件 | 位置 | 说明 | 状态 |
|------|------|------|------|
| **README_DOCKER.md** | `/root/autodl-tmp/Docker/README_DOCKER.md` | Docker使用说明（交付文档） | ✅ 已创建 |
| **DOCKER_FILES_SUMMARY.md** | `/root/autodl-tmp/Docker/DOCKER_FILES_SUMMARY.md` | 本文件 | ✅ 已创建 |
| **BUILD.md** | `/root/autodl-tmp/Docker/BUILD.md` | 构建说明文档 | ✅ 已创建 |

### 🤖 预训练模型

| 文件 | 位置 | 大小 | 用途 | 状态 |
|------|------|------|------|------|
| **swin_base_patch4_window12_384.pth** | `/root/autodl-tmp/MPSA/pretrained/` | 349MB | WebFG-400 & WebiNat-5000（共用） | ✅ 已存在 |

**说明**: 两个数据集使用同一个ImageNet-1k预训练模型。都是1K的预训练模型

---

## 📋 下一步操作

### 1. 构建Docker镜像

⚠️ **重要**：Docker文件已移至单独目录，使用以下命令构建：

```bash
cd /root/autodl-tmp/Docker
docker build -f Dockerfile -t mpsa-image:v1.0 /root/autodl-tmp/MPSA
```

或使用绝对路径：
```bash
docker build -f /root/autodl-tmp/Docker/Dockerfile -t mpsa-image:v1.0 /root/autodl-tmp/MPSA
```

预计耗时: 10-20分钟  
镜像大小: 约 5-6GB

💡 详细说明见 `BUILD.md`

### 2. 测试Docker镜像

#### 测试推理模式（快速测试）
```bash
bash run.sh
# 选择: inference + webinat5000
# 输入数据集路径: /root/autodl-tmp/database
```

#### 测试训练模式（可选，耗时较长）
```bash
bash run.sh
# 选择: train + webfg400
# 输入数据集路径: /root/autodl-tmp/database
```

### 3. 导出Docker镜像
```bash
docker save -o mpsa-image-v1.0.tar mpsa-image:v1.0
```

导出文件大小: 约 5-6GB

### 4. 准备提交包

创建提交目录并整理文件：
```bash
mkdir -p /root/autodl-tmp/submission
cd /root/autodl-tmp/Docker
cp README_DOCKER.md run.sh /root/autodl-tmp/submission/
cp mpsa-image-v1.0.tar /root/autodl-tmp/submission/
```

---

## 🎯 最终交付清单

提交给赛事方的文件：

```
submission/
├── README_DOCKER.md          # 使用说明文档（必需）
├── run.sh                    # 启动脚本（必需）
├── mpsa-image-v1.0.tar       # Docker镜像（必需，5-6GB）
└── 预训练模型说明.txt         # 预训练模型说明（可选，也可以写在README中）
```

---

## ⚠️ 重要说明

### Docker配置文件的路径映射

在Dockerfile中，Docker专用配置文件会覆盖原始配置文件：

```dockerfile
# 原始配置文件（本地使用）
configs/swin-webfg400.yaml          → data_root: /root/autodl-tmp/database/

# Docker专用配置文件
configs/swin-webfg400-docker.yaml   → data_root: /data/

# Dockerfile中的复制操作（覆盖原文件）
COPY configs/swin-webfg400-docker.yaml /app/configs/swin-webfg400.yaml
```

这样做的好处：
- ✅ 本地代码不受影响，仍然使用原始配置
- ✅ Docker容器内自动使用 `/data/` 路径
- ✅ 无需修改main.py或setup.py的核心逻辑

### 启动脚本的功能

**run.sh（宿主机）**:
- 提供交互式界面
- 验证数据集路径
- 构建docker run命令
- 传递参数给容器

**start.sh（容器内）**:
- 接收运行参数
- 动态修改配置文件
- 设置推理/训练模式
- 执行main.py
- 复制输出结果

---

## 🔍 验证检查清单

在提交前，请确认：

### 文件完整性
- [ ] Dockerfile 存在且正确
- [ ] run.sh 存在且有执行权限
- [ ] start.sh 存在且有执行权限
- [ ] README_DOCKER.md 存在且内容完整
- [ ] 两个Docker配置文件存在
- [ ] 两个预训练模型文件存在

### 功能测试
- [ ] Docker镜像成功构建
- [ ] 推理模式测试通过（webinat5000）
- [ ] 推理模式测试通过（webfg400）
- [ ] 训练模式可以正常启动
- [ ] 输出文件正确保存到outputs/

### 文档检查
- [ ] README中的数据集结构说明正确
- [ ] 预训练模型来源链接有效
- [ ] docker run命令示例正确
- [ ] 所有路径说明准确

---

## 📊 文件大小统计

| 类别 | 大小 | 说明 |
|------|------|------|
| **源代码** | ~10MB | Python文件 |
| **预训练模型** | ~779MB | 2个Swin模型 |
| **Docker基础镜像** | ~3GB | PyTorch官方镜像 |
| **Python依赖** | ~1GB | timm, opencv等 |
| **最终镜像** | ~5-6GB | 完整Docker镜像 |
| **导出tar文件** | ~5-6GB | 压缩后的镜像 |

---

## 🚀 快速开始命令

```bash
# 1. 进入Docker目录
cd /root/autodl-tmp/Docker

# 2. 构建镜像（使用MPSA作为构建上下文）
docker build -f Dockerfile -t mpsa-image:v1.0 /root/autodl-tmp/MPSA

# 3. 测试运行（推理模式）
bash run.sh

# 4. 导出镜像
docker save -o mpsa-image-v1.0.tar mpsa-image:v1.0

# 5. 验证导出
ls -lh mpsa-image-v1.0.tar
```

---

**文档生成时间**: 2025-11-04  
**项目版本**: v1.0  
**Docker镜像**: mpsa-image:v1.0

