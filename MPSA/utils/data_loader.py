# import ml_collections
import sys
from timm.data import Mixup
from torch.utils.data import DataLoader, RandomSampler, DistributedSampler, SequentialSampler
from torchvision import transforms
from torchvision.transforms import InterpolationMode
from settings.setup_functions import get_world_size
from utils.dataset import *


def build_transforms(config):
	resize = int(config.data.img_size / 0.75)
	normalized_info = normalized()
	if config.data.no_crop:
		train_base = [transforms.Resize(config.data.img_size, InterpolationMode.BICUBIC),
		              transforms.RandomHorizontalFlip()]
		test_base = [transforms.Resize(config.data.img_size, InterpolationMode.BICUBIC),
		             transforms.CenterCrop(config.data.img_size)]
	else:
		train_base = [transforms.Resize((config.data.resize, config.data.resize), InterpolationMode.BICUBIC),
		              transforms.RandomHorizontalFlip()]
		test_base = [transforms.Resize((config.data.resize, config.data.resize), InterpolationMode.BICUBIC),
		             transforms.CenterCrop(config.data.img_size)]
	to_tensor = [transforms.ToTensor(),
	             transforms.Normalize(normalized_info['standard'][:3],
	                                  normalized_info['standard'][3:])]

	if config.data.blur > 0:
		train_base += [
			transforms.RandomApply([transforms.GaussianBlur(kernel_size=(5, 5), sigma=(0.1, 5))], p=config.data.blur),
			transforms.RandomAdjustSharpness(sharpness_factor=1.5, p=config.data.blur)]
	if config.data.color > 0:
		train_base += [transforms.ColorJitter(config.data.color, config.data.color, config.data.color, config.data.hue)]
	if config.data.rotate > 0:
		train_base += [transforms.RandomRotation(config.data.rotate, InterpolationMode.BICUBIC)]
	if config.data.autoaug:
		train_base += [transforms.AutoAugment(interpolation=InterpolationMode.BICUBIC)]
	train_base += [transforms.RandomCrop(config.data.img_size, padding=config.data.padding)]

	train_transform = transforms.Compose([*train_base, *to_tensor])
	test_transform = transforms.Compose([*test_base, *to_tensor])
	return train_transform, test_transform


def build_loader(config):
	train_transform, test_transform = build_transforms(config)
	
	# 推理模式智能检测
	is_inference = detect_inference_mode(config)
	if is_inference:
		print(f"🔍 检测到推理模式，将加载竞赛测试集")

	train_set, test_set, num_classes = None, None, None
	if config.data.dataset == 'cub':
		root = os.path.join(config.data.data_root, 'CUB_200_2011')
		print(root)
		train_set = CUB(root, True, train_transform)
		test_set = CUB(root, False, test_transform)
		num_classes = 200

	elif config.data.dataset == 'cars':
		root = os.path.join(config.data.data_root, 'cars')
		train_set = Cars(root, True, train_transform)
		test_set = Cars(root, False, test_transform)
		num_classes = 196

	elif config.data.dataset == 'dogs':
		root = os.path.join(config.data.data_root, 'Dogs')
		train_set = Dogs(root, True, train_transform)
		test_set = Dogs(root, False, test_transform)
		num_classes = 120

	elif config.data.dataset == 'air':
		root = config.data.data_root
		train_set = Aircraft(root, True, train_transform)
		test_set = Aircraft(root, False, test_transform)
		num_classes = 100

	elif config.data.dataset == 'nabirds':
		root = os.path.join(config.data.data_root, 'nabirds')
		train_set = NABirds(root, True, train_transform)
		test_set = NABirds(root, False, test_transform)
		num_classes = 555

	elif config.data.dataset == 'pet':
		root = os.path.join(config.data.data_root, 'pets')
		train_set = OxfordIIITPet(root, True, train_transform)
		test_set = OxfordIIITPet(root, False, test_transform)
		num_classes = 37

	elif config.data.dataset == 'flowers':
		root = os.path.join(config.data.data_root, 'flowers')
		train_set = OxfordFlowers(root, True, train_transform)
		test_set = OxfordFlowers(root, False, test_transform)
		num_classes = 102

	elif config.data.dataset == 'food':
		root = config.data.data_root
		train_set = Food101(root, True, train_transform)
		test_set = Food101(root, False, test_transform)
		num_classes = 101

	elif config.data.dataset == 'webfg496':
		root = config.data.data_root
		if is_inference:
			# 推理模式：加载真正的竞赛测试集
			train_set = None
			test_set = WebFG496(root, False, test_transform)  # train=False
			print(f"✅ 加载WebFG496竞赛测试集: {len(test_set)} 样本")
		else:
			# 训练模式：保持现有验证集划分逻辑
			val_split = getattr(config.data, 'val_split', 0.2)
			
			# 训练集（80%的原训练数据）
			train_set = WebFG496(root, True, train_transform, val_split=val_split)
			train_set._split_train_val()  # 调用划分方法获取训练集部分
			
			# 验证集（20%的原训练数据）- 作为test_set返回以复用原有验证逻辑
			test_set = WebFG496(root, True, test_transform, val_split=val_split)
			test_set.is_validation = True  # 标记为验证集
			test_set._split_train_val()   # 重新划分获取验证集样本
		
		num_classes = 496

	elif config.data.dataset == 'webfg400':
		root = config.data.data_root
		if is_inference:
			# 推理模式：加载真正的竞赛测试集
			train_set = None
			test_set = WebFG400(root, False, test_transform)  # train=False
			print(f"✅ 加载WebFG400竞赛测试集: {len(test_set)} 样本")
		else:
			# 训练模式：保持现有验证集划分逻辑（复用WebFG496逻辑）
			val_split = getattr(config.data, 'val_split', 0.2)
			
			# 训练集（80%的原训练数据）
			train_set = WebFG400(root, True, train_transform, val_split=val_split)
			train_set._split_train_val()  # 调用划分方法获取训练集部分
			
			# 验证集（20%的原训练数据）- 作为test_set返回以复用原有验证逻辑
			test_set = WebFG400(root, True, test_transform, val_split=val_split)
			test_set.is_validation = True  # 标记为验证集
			test_set._split_train_val()   # 重新划分获取验证集样本
		
		num_classes = 400

	elif config.data.dataset == 'webinat5000':
		root = config.data.data_root
		if is_inference:
			# 推理模式：加载真正的竞赛测试集
			train_set = None
			test_set = WebiNat5000(root, False, test_transform)  # train=False
			print(f"✅ 加载WebiNat5000竞赛测试集: {len(test_set)} 样本")
		else:
			# 训练模式：保持现有验证集划分逻辑（复用WebiNat5089长尾策略）
			val_split = getattr(config.data, 'val_split', 0.2)
			
			# 训练集
			train_set = WebiNat5000(root, True, train_transform, val_split=val_split)
			train_set._split_train_val()  # 调用划分方法获取训练集部分
			
			# 验证集 - 作为test_set返回以复用原有验证逻辑
			test_set = WebiNat5000(root, True, test_transform, val_split=val_split)
			test_set.is_validation = True  # 标记为验证集
			test_set._split_train_val()   # 重新划分获取验证集样本
		
		num_classes = 5000

	elif config.data.dataset == 'webinat5089':
		root = config.data.data_root
		if is_inference:
			# 推理模式：加载真正的竞赛测试集  
			train_set = None
			test_set = WebiNat5089(root, False, test_transform)  # train=False
			print(f"✅ 加载WebiNat5089竞赛测试集: {len(test_set)} 样本")
		else:
			# 训练模式：保持现有验证集划分逻辑
			val_split = getattr(config.data, 'val_split', 0.2)
			
			# 训练集（80%的原训练数据）
			train_set = WebiNat5089(root, True, train_transform, val_split=val_split)
			train_set._split_train_val()  # 调用划分方法获取训练集部分
			
			# 验证集（20%的原训练数据）- 作为test_set返回以复用原有验证逻辑
			test_set = WebiNat5089(root, True, test_transform, val_split=val_split)
			test_set.is_validation = True  # 标记为验证集
			test_set._split_train_val()   # 重新划分获取验证集样本
		
		num_classes = 5089
	# 针对H800+大规模数据集优化的worker配置
	# 基于176核CPU的最优配置：GPU核心数比例 + 数据增强复杂度考虑
	num_workers = 32 if sys.platform != 'win32' else 0  # 大幅提升并发worker数
	if config.local_rank == -1:
		train_sampler = RandomSampler(train_set) if train_set is not None else None
		test_sampler = SequentialSampler(test_set)
	else:
		train_sampler = DistributedSampler(train_set, num_replicas=get_world_size(),
		                                   rank=config.local_rank, shuffle=True) if train_set is not None else None
		test_sampler = DistributedSampler(test_set)
	
	train_loader = DataLoader(train_set, sampler=train_sampler, batch_size=config.data.batch_size,
	                          num_workers=num_workers, drop_last=True, pin_memory=True, 
	                          persistent_workers=True, prefetch_factor=4) if train_set is not None else None
	test_loader = DataLoader(test_set, sampler=test_sampler, batch_size=config.data.batch_size,
	                         num_workers=num_workers, shuffle=False, drop_last=False, pin_memory=True,
	                         persistent_workers=True, prefetch_factor=4)

	mixup_fn = None
	mixup_active = config.data.mixup > 0. or config.data.cutmix > 0.
	if mixup_active:
		mixup_fn = Mixup(
			mixup_alpha=config.data.mixup, cutmix_alpha=config.data.cutmix,
			label_smoothing=config.model.label_smooth, num_classes=num_classes)

	return train_loader, test_loader, num_classes, len(train_set) if train_set is not None else 0, len(test_set), mixup_fn


def normalized():
	normalized_info = dict()
	normalized_info['standard'] = (0.485, 0.456, 0.406, 0.229, 0.224, 0.225)
	return normalized_info


def detect_inference_mode(config):
	"""智能检测推理模式"""
	# 方式1：显式inference_mode参数
	if hasattr(config.misc, 'inference_mode') and config.misc.inference_mode:
		return True
	
	# 方式2：eval_mode参数（向后兼容）
	if hasattr(config.misc, 'eval_mode') and config.misc.eval_mode:
		return True
	
	# 注释掉错误的第3种检测：resume不为空不代表推理模式
	# 因为resume也可以用于从检查点继续训练
	# if hasattr(config.model, 'resume') and config.model.resume:
	#     return True
		
	return False
