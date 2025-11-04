# Docker化项目目录结构说明

## 📁 完整目录结构

```
/root/autodl-tmp/
│
├── MPSA/                              # 🔧 项目源代码目录（保持清爽）
│   ├── models/                        # 模型定义
│   ├── utils/                         # 工具函数
│   ├── settings/                      # 配置系统
│   ├── configs/                       # 配置文件
│   │   ├── swin-webfg400.yaml         # WebFG-400本地配置
│   │   ├── swin-webinat5000.yaml      # WebiNat-5000本地配置
│   │   ├── swin-webfg400-docker.yaml  # Docker专用配置
│   │   └── swin-webinat5000-docker.yaml  # Docker专用配置
│   ├── visualize/                     # 可视化脚本
│   ├── pretrained/                    # 预训练模型
│   │   └── swin_base_patch4_window12_384.pth (349MB)
│   ├── output/                        # 训练输出
│   ├── main.py                        # 主程序
│   ├── setup.py                       # 配置加载
│   ├── README.md                      # 项目原始说明
│   └── requirements.txt               # 完整依赖列表
│
├── Docker/                            # 🐳 Docker化文件目录（独立管理）
│   ├── Dockerfile                     # 镜像构建文件
│   ├── .dockerignore                  # 忽略文件配置
│   ├── requirements_docker.txt        # 精简依赖列表
│   ├── run.sh                         # 宿主机启动脚本
│   ├── start.sh                       # 容器内执行脚本
│   ├── README_DOCKER.md               # Docker使用说明
│   ├── DOCKER_FILES_SUMMARY.md        # 文件清单
│   ├── BUILD.md                       # 构建说明
│   ├── STRUCTURE.md                   # 本文件（目录结构说明）
│   └── configs/                       # 配置文件备份
│       ├── swin-webfg400-docker.yaml
│       └── swin-webinat5000-docker.yaml
│
├── database/                          # 📊 数据集目录（不打包进镜像）
│   ├── webfg400_train/
│   ├── webfg400_test_B/
│   ├── webinat5000_train/
│   └── webinat5000_test_B/
│
└── submission/                        # 📦 提交目录（构建后创建）
    ├── README_DOCKER.md
    ├── run.sh
    └── mpsa-image-v1.0.tar (5-6GB)
```

---

## 🎯 设计理念

### 1. 职责分离
- **MPSA/**：项目源代码，保持原始结构
- **Docker/**：Docker化相关文件，统一管理

### 2. 保持清爽
- MPSA目录不包含Docker相关文件
- Docker目录独立，便于维护和提交

### 3. 灵活构建
- Dockerfile在Docker/目录
- 构建时使用MPSA/作为上下文
- 配置文件在MPSA/中维护，Docker/中备份

---

## 🔄 文件流转关系

### 构建时
```
Docker/Dockerfile
    ↓ (读取构建指令)
MPSA/* (作为构建上下文)
    ↓ (COPY命令复制文件)
Docker镜像
```

### 运行时
```
宿主机: Docker/run.sh
    ↓ (启动容器)
容器内: /app/start.sh
    ↓ (执行程序)
容器内: /app/main.py
    ↓ (输出结果)
宿主机: outputs/
```

### 提交时
```
Docker/README_DOCKER.md  ─┐
Docker/run.sh            ─┤
Docker/mpsa-image.tar    ─┤→ submission/
```

---

## 📝 配置文件说明

### MPSA/configs/

| 文件 | 用途 | data_root |
|------|------|-----------|
| `swin-webfg400.yaml` | 本地训练 | `/root/autodl-tmp/database/` |
| `swin-webinat5000.yaml` | 本地训练 | `/root/autodl-tmp/database/` |
| `swin-webfg400-docker.yaml` | Docker构建 | `/data/` |
| `swin-webinat5000-docker.yaml` | Docker构建 | `/data/` |

### Docker/configs/
- 配置文件的副本（备份）
- 不参与构建（Dockerfile从MPSA/configs/复制）

---

## 🚀 工作流程

### 开发阶段
```bash
# 在MPSA目录工作
cd /root/autodl-tmp/MPSA
python main.py  # 本地训练/测试
```

### Docker化阶段
```bash
# 在Docker目录工作
cd /root/autodl-tmp/Docker

# 构建镜像
docker build -f Dockerfile -t mpsa-image:v1.0 /root/autodl-tmp/MPSA

# 测试镜像
bash run.sh

# 导出镜像
docker save -o mpsa-image-v1.0.tar mpsa-image:v1.0
```

### 提交阶段
```bash
# 准备提交包
mkdir -p /root/autodl-tmp/submission
cd /root/autodl-tmp/Docker
cp README_DOCKER.md run.sh mpsa-image-v1.0.tar /root/autodl-tmp/submission/
```

---

## ✅ 优势

1. **目录清爽**：MPSA目录只包含项目代码
2. **管理集中**：Docker文件统一在Docker/目录
3. **易于维护**：修改Docker相关文件不影响源代码
4. **便于提交**：Docker/目录包含所有需要交付的文件
5. **版本控制友好**：可以单独管理Docker/目录

---

**最后更新**: 2025-11-04

