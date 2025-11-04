# MPSA 评测方操作指南

本文档面向赛事/评测方，说明在收到提交包后如何复现训练或推理流程。提交包包含以下文件：

- `mpsa-image-v1.0.tar`：参赛方构建好的 Docker 镜像
- `run.sh`：宿主机启动脚本（位于 `Docker/` 目录）
- `README_DOCKER.md`：详细功能说明，可做进一步参考

## 1. 环境要求

有显卡，然后显存大一点就行

## 2. 准备工作

1. 将提交包解压至任意目录，比如：


   MPSA/
   ├── mpsa-image-v1.0.tar
   ├── run.sh
   └── README_DOCKER.md
   ```

2. 准备数据集根目录，并保持以下子目录结构：

   - WebFG-400：`webfg400_train/train/`、`webfg400_test_B/test_B/`
   - WebiNat-5000：`webinat5000_train/train/`、`webinat5000_test_B/test_B/`

   假设评测方的数据集位于 `/data/mpsa/`。

## 3. 导入 Docker 镜像

在包含 `mpsa-image-v1.0.tar` 的目录执行：

```bash
docker load -i mpsa-image-v1.0.tar
```

镜像导入成功后，可通过下列命令确认：

```bash
docker images | grep mpsa-image
```

若显示 `mpsa-image    v1.0` 即表示镜像已就绪。

## 4. 启动训练 / 推理

1. 切换到 `run.sh` 所在目录（示例：`MPSA/`）。
2. 赋予脚本执行权限（若已为可执行，可跳过）：

   ```bash
   chmod +x run.sh
   ```

3. 运行脚本并按照提示选择模式、数据集及数据路径：

   ```bash
   bash run.sh
   ```

   - **运行模式**：选择 `train`（训练）或 `inference`（推理）
   - **数据集**：选择 `webfg400` 或 `webinat5000`
   - **数据路径**：输入步骤 2 中你们比赛方电脑上的准备的数据集根目录（示例 `/data/mpsa`）

脚本会自动：

- 挂载数据目录到容器 `/data`
- 将宿主机 `./outputs` 目录挂载到容器 `/outputs`
- 在容器内调用 `/app/start.sh` 完成训练或推理流程

## 5. 结果查看

- 训练模式：模型权重与日志保存在宿主机当前目录下的 `outputs/` 子目录
- 推理模式：预测结果 CSV 文件同步写入 `outputs/`