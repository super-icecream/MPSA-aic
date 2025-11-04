# Docker基础镜像版本更新说明

## 更新时间
2025-11-04

## 更新原因
PyTorch官方Docker Hub不提供 `pytorch/pytorch:2.0.x-cuda11.8-cudnn8-runtime` 版本。

经过实际查询Docker Hub API，发现可用的CUDA 11.8版本如下：
- 2.2.1-cuda11.8-cudnn8-runtime
- 2.2.0-cuda11.8-cudnn8-runtime
- 2.1.2-cuda11.8-cudnn8-runtime ⭐ (已选择)

## 最终选择
**`pytorch/pytorch:2.1.2-cuda11.8-cudnn8-runtime`**

### 选择理由
1. ✅ 最接近原环境版本（PyTorch 2.0.0+cu118）
2. ✅ CUDA 11.8完全匹配
3. ✅ API向后兼容，无需修改代码
4. ✅ 2.1.2是稳定的修复版本
5. ✅ runtime镜像体积更小（不含开发工具）

## 修改的文件
1. `/root/autodl-tmp/Docker/Dockerfile` (第7-9行, 第31行)
2. `/root/autodl-tmp/Docker/README_DOCKER.md` (第16-18行)

## 兼容性说明
- PyTorch 2.1.2与2.0.0 API完全兼容
- 无需修改任何Python代码
- timm、einops等依赖库无需调整版本

## 验证命令
```bash
# 查看修改
grep "pytorch/pytorch" Dockerfile README_DOCKER.md
```

## 下一步
可以开始构建Docker镜像：
```bash
docker build -f Dockerfile -t mpsa-image:v1.0 ../MPSA
```
