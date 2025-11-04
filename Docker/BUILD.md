# Docker镜像构建说明

## 📁 目录结构

```
/root/autodl-tmp/
├── MPSA/                          # 项目源代码目录
│   ├── models/
│   ├── utils/
│   ├── configs/
│   │   ├── swin-webfg400-docker.yaml    # Docker配置
│   │   └── swin-webinat5000-docker.yaml # Docker配置
│   ├── main.py
│   └── ...
└── Docker/                        # Docker相关文件（本目录）
    ├── Dockerfile                 # 镜像构建文件
    ├── .dockerignore             # 忽略文件配置
    ├── requirements_docker.txt   # Python依赖
    ├── run.sh                    # 宿主机启动脚本
    ├── start.sh                  # 容器内执行脚本
    ├── README_DOCKER.md          # 使用说明文档
    ├── DOCKER_FILES_SUMMARY.md   # 文件清单
    ├── BUILD.md                  # 本文件
    └── configs/                  # 配置文件副本
        ├── swin-webfg400-docker.yaml
        └── swin-webinat5000-docker.yaml
```

---

## 🔨 构建Docker镜像

### 方法1：在Docker目录构建（推荐）

```bash
cd /root/autodl-tmp/Docker
docker build -f Dockerfile -t mpsa-image:v1.0 /root/autodl-tmp/MPSA
```

**说明**：
- `-f Dockerfile`：指定Dockerfile位置（当前目录）
- `-t mpsa-image:v1.0`：镜像名称和标签
- `/root/autodl-tmp/MPSA`：构建上下文目录（源代码位置）

### 方法2：使用绝对路径

```bash
docker build -f /root/autodl-tmp/Docker/Dockerfile \
             -t mpsa-image:v1.0 \
             /root/autodl-tmp/MPSA
```

---

## ⚙️ 构建参数说明

### 为什么使用MPSA作为构建上下文？

Dockerfile中的COPY命令需要访问MPSA目录下的文件：
- `COPY models/ /app/models/`
- `COPY utils/ /app/utils/`
- `COPY main.py /app/main.py`
- 等等

因此，构建上下文必须是MPSA目录。

### Docker配置文件的处理

Docker专用配置文件存在两处：
1. `/root/autodl-tmp/MPSA/configs/swin-*-docker.yaml`（源文件）
2. `/root/autodl-tmp/Docker/configs/swin-*-docker.yaml`（副本，备份）

构建时使用MPSA目录中的配置文件。

---

## 🚀 完整构建流程

```bash
# 1. 进入Docker目录
cd /root/autodl-tmp/Docker

# 2. 构建镜像（预计10-20分钟）
docker build -f Dockerfile -t mpsa-image:v1.0 /root/autodl-tmp/MPSA

# 3. 验证镜像
docker images | grep mpsa-image

# 4. 测试运行
bash run.sh
```

---

## 📦 导出镜像

```bash
cd /root/autodl-tmp/Docker
docker save -o mpsa-image-v1.0.tar mpsa-image:v1.0
ls -lh mpsa-image-v1.0.tar
```

---

## 📤 提交给赛事方

提交以下文件：

```
submission/
├── README_DOCKER.md          # 使用说明（从Docker/复制）
├── run.sh                    # 启动脚本（从Docker/复制）
└── mpsa-image-v1.0.tar       # Docker镜像（约5-6GB）
```

准备命令：
```bash
mkdir -p /root/autodl-tmp/submission
cd /root/autodl-tmp/Docker
cp README_DOCKER.md run.sh /root/autodl-tmp/submission/
cp mpsa-image-v1.0.tar /root/autodl-tmp/submission/
```

---

## ❓ 常见问题

### Q: 为什么不把Dockerfile放在MPSA目录？
A: 为了保持项目目录清爽，Docker相关文件统一管理在Docker/目录。

### Q: 构建时找不到文件怎么办？
A: 确保使用正确的构建命令，指定MPSA为构建上下文。

### Q: 如何更新配置文件？
A: 修改`/root/autodl-tmp/MPSA/configs/*-docker.yaml`后重新构建镜像。

---

**最后更新**: 2025-11-04  
**Docker镜像版本**: mpsa-image:v1.0

