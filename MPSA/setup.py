from settings.defaults import _C
from settings.setup_functions import *
root = os.path.dirname(os.path.abspath(__file__))
config = _C.clone()
# cfg_file = os.path.join('configs','baseline', 'swin_tiny.yaml')
# cfg_file = os.path.join('../configs', 'eval', 'eval.yaml')
# cfg_file = os.path.join('configs', 'eval', 'eval_base.yaml')
# cfg_file = os.path.join('configs', 'swin-webinat5089.yaml')  # WebiNat5089数据集
cfg_file = os.path.join('configs', 'swin-webinat5000.yaml')  # WebiNat5000数据集（当前使用）✨
# cfg_file = os.path.join('configs', 'swin-webfg496.yaml')     # WebFG496数据集
# cfg_file = os.path.join('configs', 'swin-webfg400.yaml')       # WebFG400数据集
config = SetupConfig(config, cfg_file)
config.defrost()

# ============================================================================
# 推理配置区域 - 为不同数据集设置训练好的模型路径
# ============================================================================
# WebFG496数据集推理模型路径
webfg496_model_path = "/root/autodl-tmp/MPSA/output/webfg496/Ours 09-02_01-50/checkpoint.bin"

# WebiNat5089数据集推理模型路径  
webinat5089_model_path = "/root/autodl-tmp/MPSA/output/webinat5089/Ours 09-02_21-05/checkpoint.bin"

# WebiNat5000数据集推理模型路径（新增）
webinat5000_model_path = "/root/autodl-tmp/MPSA/output/webinat5000/Ours 10-31_20-38/BE30/checkpoint.bin"  # ✅ 已更新为最新训练模型

# WebFG400数据集推理模型路径
webfg400_model_path = "/root/autodl-tmp/MPSA/output/webfg400/Ours XX-XX_XX-XX/checkpoint.bin"  # ← 训练完成后替换为实际路径

# 根据当前数据集自动选择对应的模型路径
# 🔄 推理模式：已启用模型加载
if config.data.dataset == 'webfg496':
    config.model.resume = webfg496_model_path
elif config.data.dataset == 'webinat5089':
    config.model.resume = webinat5089_model_path
elif config.data.dataset == 'webinat5000':
    config.model.resume = webinat5000_model_path
elif config.data.dataset == 'webfg400':
    config.model.resume = webfg400_model_path
# ============================================================================

## Log Name and Perferences
config.write = True
config.train.checkpoint = True
config.misc.exp_name = f'{config.data.dataset}'
# config.misc.exp_name = f'cars'
# config.misc.log_name = f'pr {config.parameters.parts_ratio}+pd {config.parameters.parts_drop}'
config.misc.log_name = f'Ours'
try:
	config.cuda_visible = '4,3,1,6,2,0' if int(os.environ['WORLD_SIZE']) > 2 else '0,1'
	# config.cuda_visible = '4,3,6,0,2,1' if int(os.environ['WORLD_SIZE']) > 2 else '0,1'
except:
	config.cuda_visible = '0,1'

# Environment Settings
config.data.log_path = os.path.join(config.misc.output, config.misc.exp_name, config.misc.log_name
                                    + time.strftime(' %m-%d_%H-%M', time.localtime()))

config.model.pretrained = os.path.join(config.model.pretrained,
                                       config.model.name + config.model.pre_version + config.model.pre_suffix)
os.environ['CUDA_VISIBLE_DEVICES'] = config.cuda_visible
os.environ['OMP_NUM_THREADS'] = '1'

# Setup Functions
config.nprocess, config.local_rank = SetupDevice()
config.data.data_root, config.data.batch_size = LocateDatasets(config)
config.train.lr = ScaleLr(config)
log = SetupLogs(config, config.local_rank)
if config.write and config.local_rank in [-1, 0]:
	with open(config.data.log_path + '/config.json', "w") as f:
		f.write(config.dump())
config.freeze()
SetSeed(config)



