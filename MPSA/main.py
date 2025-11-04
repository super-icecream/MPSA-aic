import sys
import torch
import warnings
import logging
import os
from PIL import Image

# 设置PIL图像大小限制，适应大规模数据集中的高分辨率图像
Image.MAX_IMAGE_PIXELS = 200000000  # 增加到200M像素限制

# 抑制PIL警告但保留重要警告
warnings.filterwarnings('ignore', 'Palette images with Transparency expressed in bytes should be converted to RGBA images', UserWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='PIL')
warnings.filterwarnings('ignore', 'Image size .* exceeds limit .* could be decompression bomb DOS attack', UserWarning)

# 将PIL的logger重定向到文件，避免终端输出
pil_logger = logging.getLogger('PIL')
pil_logger.setLevel(logging.WARNING)

from timm.utils import AverageMeter, accuracy, NativeScaler
from timm.loss import LabelSmoothingCrossEntropy, SoftTargetCrossEntropy
from tqdm import tqdm

from models.build import build_models, freeze_backbone
from setup import config, log
from utils.data_loader import build_loader
from utils.eval import *
from utils.info import *
from utils.optimizer import build_optimizer
from utils.scheduler import build_scheduler


def detect_inference_mode(config):
	"""推理模式检测"""
	if hasattr(config.misc, 'inference_mode') and config.misc.inference_mode:
		return True
	if hasattr(config.misc, 'eval_mode') and config.misc.eval_mode:
		return True
	# 注释掉错误的检测：resume不为空不代表推理模式
	# 因为resume也可以用于从检查点继续训练
	# if hasattr(config.model, 'resume') and config.model.resume:
	#	return True
	return False


def extract_relative_path(full_path, dataset):
	"""提取符合竞赛要求的相对路径格式"""
	if dataset == 'webfg496':
		# WebFG496格式：提取 "test/new_val/0000.jpg" 格式
		parts = full_path.split('/')
		if 'new_val' in parts:
			idx = parts.index('new_val')
			return '/'.join(parts[idx-1:])  # "test/new_val/xxxx.jpg"
	elif dataset == 'webfg400':
		# WebFG400格式：仅提取文件名（竞赛要求）
		return os.path.basename(full_path)  # "xxxxxxxxxxxx.jpg"
	elif dataset == 'webinat5089':
		# WebiNat5089格式：仅提取文件名
		return os.path.basename(full_path)  # "0001.jpg"
	elif dataset == 'webinat5000':
		# WebiNat5000格式：仅提取文件名（与webinat5089相同）
		return os.path.basename(full_path)  # "xxxxxxxxxxxx.jpg"
	return full_path


def save_predictions_to_file(paths, predictions, config):
	"""保存预测结果到竞赛要求的CSV格式文件"""
	
	# 根据数据集确定输出文件名（符合竞赛要求）
	dataset_to_filename = {
		'webfg496': 'pred_results_web496.csv',
		'webfg400': 'pred_results_web400.csv',  # 竞赛要求：WebFG-400
		'webinat5089': 'pred_results_web5000.csv',  # 竞赛要求：WebiNat-5000（旧数据集，但文件名要求相同）
		'webinat5000': 'pred_results_web5000.csv'  # ✅ 竞赛要求：WebiNat-5000（新数据集）
	}
	
	filename = dataset_to_filename.get(config.data.dataset, f'pred_results_{config.data.dataset}.csv')
	
	# 推理模式下直接使用log_path目录，与训练日志文件保存在同一位置
	output_dir = config.data.log_path
	output_path = os.path.join(output_dir, filename)
	
	# 确保输出目录存在
	os.makedirs(os.path.dirname(output_path), exist_ok=True)
	
	# 写入CSV格式预测结果（竞赛要求）
	# 格式：filename, label（逗号后有空格，label为4位数字补0）
	with open(output_path, 'w', encoding='utf-8') as f:
		for path, pred in zip(paths, predictions):
			# 类别补0到4位数字（竞赛要求）
			label_str = str(int(pred)).zfill(4)
			# CSV格式：filename, label（逗号+空格分隔）
			f.write(f'{path}, {label_str}\n')
	
	print(f"✅ 预测结果已保存至: {output_path}")
	print(f"📊 总计预测样本数: {len(predictions)}")
	print(f"📝 输出格式: CSV (竞赛标准格式)")
	print(f"📄 文件名: {filename}")
	if len(paths) > 0 and len(predictions) > 0:
		print(f"💡 示例格式: {paths[0]}, {str(int(predictions[0])).zfill(4)}")


try:
	from torch.utils.tensorboard import SummaryWriter
except:
	pass


def build_model(config, num_classes):
	model = build_models(config, num_classes)
	# if torch.__version__[0] == '2' and sys.platform != 'win32':
	# 	# torch.set_float32_matmul_precision('high')
	# 	model = torch.compile(model)
	model.to(config.device)
	freeze_backbone(model, config.train.freeze_backbone)
	model_without_ddp = model
	n_parameters = count_parameters(model)

	config.defrost()
	config.model.num_classes = num_classes
	config.model.parameters = f'{n_parameters:.3f}M'
	config.freeze()
	if config.local_rank in [-1, 0]:
		PSetting(log, 'Model Structure', config.model.keys(), config.model.values(), rank=config.local_rank)
		log.save(model)
	return model, model_without_ddp


def main(config):
	# 配置Python logging模块，将图像处理相关的日志重定向
	if config.write:
		os.makedirs(config.data.log_path, exist_ok=True)
		logging.basicConfig(
			level=logging.WARNING,
			format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
			handlers=[
				logging.FileHandler(os.path.join(config.data.log_path, 'system.log'), mode='a'),
			]
		)
		
		# 抑制PIL相关的终端输出
		logging.getLogger('PIL').setLevel(logging.ERROR)
	
	# Timer
	total_timer = Timer()
	prepare_timer = Timer()
	prepare_timer.start()
	train_timer = Timer()
	eval_timer = Timer()
	total_timer.start()
	# Initialize the Tensorboard Writer
	writer = None
	if config.write:
		try:
			writer = SummaryWriter(config.data.log_path)
		except:
			pass

	# Prepare dataset
	train_loader, test_loader, num_classes, train_samples, test_samples, mixup_fn = build_loader(config)
	step_per_epoch = len(train_loader) if train_loader is not None else 1  # 推理模式下设置为1避免scheduler错误
	total_batch_size = config.data.batch_size * get_world_size()
	steps = config.train.epochs * step_per_epoch

	# Build model
	model, model_without_ddp = build_model(config, num_classes)

	if config.local_rank != -1:
		model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[config.local_rank],
		                                                  broadcast_buffers=False,
		                                                  find_unused_parameters=False)
	# backbone_low_lr = config.model.type.lower() == 'resnet'
	# optimizer = build_optimizer(config, model, backbone_low_lr)
	optimizer = build_optimizer(config, model, False)
	loss_scaler = NativeScalerWithGradNormCount()
	scheduler = build_scheduler(config, optimizer, step_per_epoch)

	# Determine criterion
	best_acc, best_epoch, train_accuracy = 0., 0., 0.

	if config.data.mixup > 0.:
		criterion = SoftTargetCrossEntropy()
	elif config.model.label_smooth:
		criterion = LabelSmoothingCrossEntropy(smoothing=config.model.label_smooth)
	else:
		criterion = torch.nn.CrossEntropyLoss()

	# Function Mode
	if config.model.resume:
		best_acc = load_checkpoint(config, model, optimizer, scheduler, loss_scaler, log)
		best_epoch = config.train.start_epoch
		accuracy, loss = valid(config, model, test_loader, best_epoch, train_accuracy,writer,True)
		log.info(f'Epoch {best_epoch+1:^3}/{config.train.epochs:^3}: Accuracy {accuracy:2.3f}    '
		         f'BA {best_acc:2.3f}    BE {best_epoch+1:3}    '
		         f'Loss {loss:1.4f}    TA {train_accuracy * 100:2.2f}')
		
		# 推理模式或eval模式下直接返回，不进入训练循环
		if config.misc.eval_mode or detect_inference_mode(config):
			return

	if config.misc.throughput:
		throughput(test_loader, model, log, config.local_rank)
		return

	# Record result in Markdown Table
	mark_table = PMarkdownTable(log, ['Epoch', 'Accuracy', 'Best Accuracy',
	                                  'Best Epoch', 'Loss'], rank=config.local_rank)

	# End preparation
	torch.cuda.synchronize()
	prepare_time = prepare_timer.stop()
	PSetting(log, 'Training Information',
	         ['Train samples', 'Test samples', 'Total Batch Size', 'Load Time', 'Train Steps',
	          'Warm Epochs'],
	         [train_samples, test_samples, total_batch_size,
	          f'{prepare_time:.0f}s', steps, config.train.warmup_epochs],
	         newline=2, rank=config.local_rank)

	# Train Function
	sub_title(log, 'Start Training', rank=config.local_rank)
	
	# 推理模式检测：统一使用detect_inference_mode()函数
	is_inference_mode = detect_inference_mode(config)
	
	for epoch in range(config.train.start_epoch, config.train.epochs):
		train_timer.start()
		if config.local_rank != -1 and train_loader is not None:
			train_loader.sampler.set_epoch(epoch)
		# list1 = list(model.named_parameters())
		# print(list1[76])

		# 修复：推理模式下跳过训练，只执行验证
		if not config.misc.eval_mode and not is_inference_mode and train_loader is not None:
			train_accuracy = train_one_epoch(config, model, criterion, train_loader, optimizer,
			                                 epoch, scheduler, loss_scaler, mixup_fn, writer)
		else:
			# 推理模式或eval模式下设置默认训练准确率
			train_accuracy = 0.0
		train_timer.stop()

		# Eval Function
		eval_timer.start()
		if (epoch + 1) % config.misc.eval_every == 0 or epoch + 1 == config.train.epochs:
			accuracy, loss = valid(config, model, test_loader, epoch, train_accuracy, writer,False)
			if config.local_rank in [-1, 0]:
				if best_acc < accuracy:
					best_acc = accuracy
					best_epoch = epoch + 1
					if config.write and epoch > 1 and config.train.checkpoint:
						save_checkpoint(config, epoch, model, best_acc, optimizer, scheduler, loss_scaler, log)
				log.info(f'Epoch {epoch + 1:^3}/{config.train.epochs:^3}: Accuracy {accuracy:2.3f}    '
				         f'BA {best_acc:2.3f}    BE {best_epoch:3}    '
				         f'Loss {loss:1.4f}    TA {train_accuracy * 100:2.2f}')
				if config.write:
					mark_table.add(log, [epoch + 1, f'{accuracy:2.3f}',
					                     f'{best_acc:2.3f}', best_epoch, f'{loss:1.5f}'], rank=config.local_rank)
			pass  # Eval
		eval_timer.stop()
		pass  # Train

	# Finish Training
	if writer is not None:
		writer.close()
	train_time = train_timer.sum / 60
	eval_time = eval_timer.sum / 60
	total_time = train_time + eval_time
	total_time_true = total_timer.stop()
	total_time_true = total_time_true/60
	PSetting(log, "Finish Training",
	         ['Best Accuracy', 'Best Epoch', 'Training Time', 'Testing Time', 'Syncthing Time','Total Time'],
	         [f'{best_acc:2.3f}', best_epoch, f'{train_time:.2f} min', f'{eval_time:.2f} min', f'{total_time_true-total_time:.2f} min' ,f'{total_time_true:.2f} min'],
	         newline=2, rank=config.local_rank)


def train_one_epoch(config, model, criterion, train_loader, optimizer, epoch, scheduler, loss_scaler, mixup_fn=None,
                    writer=None):
	model.train()
	optimizer.zero_grad()

	step_per_epoch = len(train_loader)
	loss_meter = AverageMeter()
	norm_meter = AverageMeter()
	scaler_meter = AverageMeter()
	epochs = config.train.epochs

	loss1_meter = AverageMeter()
	loss2_meter = AverageMeter()
	loss3_meter = AverageMeter()

	p_bar = tqdm(total=step_per_epoch,
	             desc=f'Train {epoch + 1:^3}/{epochs:^3}',
	             dynamic_ncols=True,
	             ascii=True,
	             disable=config.local_rank not in [-1, 0])
	all_preds, all_label = None, None
	for step, (x, y) in enumerate(train_loader):
		global_step = epoch * step_per_epoch + step
		x, y = x.cuda(non_blocking=True), y.cuda(non_blocking=True)
		if mixup_fn:
			x, y = mixup_fn(x, y)
		with torch.cuda.amp.autocast(enabled=config.misc.amp):
			if config.model.baseline_model:
				logits = model(x)
			else:
				logits = model(x, y)
		logits, loss, other_loss = loss_in_iters(logits, y, criterion)

		is_second_order = hasattr(optimizer, 'is_second_order') and optimizer.is_second_order
		grad_norm = loss_scaler(loss, optimizer, clip_grad=config.train.clip_grad,
		                        parameters=model.parameters(), create_graph=is_second_order)

		optimizer.zero_grad()
		scheduler.step_update(global_step + 1)
		loss_scale_value = loss_scaler.state_dict()["scale"]

		if mixup_fn is None:
			preds = torch.argmax(logits, dim=-1)
			all_preds, all_label = save_preds(preds, y, all_preds, all_label)
		torch.cuda.synchronize()

		if grad_norm is not None:
			norm_meter.update(grad_norm)
		scaler_meter.update(loss_scale_value)
		loss_meter.update(loss.item(), y.size(0))

		lr = optimizer.param_groups[0]['lr']
		if writer:
			writer.add_scalar("train/loss", loss_meter.val, global_step)
			writer.add_scalar("train/lr", lr, global_step)
			writer.add_scalar("train/grad_norm", norm_meter.val, global_step)
			writer.add_scalar("train/scaler_meter", scaler_meter.val, global_step)
			if other_loss:
				try:
					loss1_meter.update(other_loss[0].item(), y.size(0))
					loss2_meter.update(other_loss[1].item(), y.size(0))
					loss3_meter.update(other_loss[2].item(), y.size(0))
				except:
					pass

				writer.add_scalar("losses/t_loss", loss_meter.val, global_step)
				writer.add_scalar("losses/1_loss", loss1_meter.val, global_step)
				writer.add_scalar("losses/2_loss", loss2_meter.val, global_step)
				writer.add_scalar("losses/3_loss", loss3_meter.val, global_step)

		# set_postfix require dic input
		p_bar.set_postfix(loss="%2.5f" % loss_meter.avg, lr="%.2e" % lr, gn="%1.4f" % norm_meter.avg)
		p_bar.update()

	# After Training an Epoch
	p_bar.close()
	train_accuracy = eval_accuracy(all_preds, all_label, config) if mixup_fn is None else 0.0
	return train_accuracy


def loss_in_iters(output, targets, criterion):
	if not isinstance(output, (list, tuple)):
		return output, criterion(output, targets), None
	else:
		logits, loss = output
		if not isinstance(loss, (list, tuple)):
			return logits, loss, None
		else:
			return logits, loss[0], loss[1:]

@torch.no_grad()
def valid(config, model, test_loader, epoch=-1, train_acc=0.0, writer=None,save_feature=False):
	criterion = torch.nn.CrossEntropyLoss()
	model.eval()

	# 推理模式检测和预测结果收集
	is_inference = detect_inference_mode(config)
	all_predictions = []
	all_paths = []

	step_per_epoch = len(test_loader)
	p_bar = tqdm(total=step_per_epoch,
	             desc=f'Valid {(epoch + 1) // config.misc.eval_every:^3}/{math.ceil(config.train.epochs / config.misc.eval_every):^3}',
	             dynamic_ncols=True,
	             ascii=True,
	             disable=config.local_rank not in [-1, 0])

	loss_meter = AverageMeter()
	acc_meter = AverageMeter()
	saved_feature,saved_labels = [],[]
	for step, (x, y) in enumerate(test_loader):
		x, y = x.cuda(non_blocking=True), y.cuda(non_blocking=True)

		with torch.cuda.amp.autocast(enabled=config.misc.amp):
			logits = model(x)

		# 推理模式下收集预测结果
		if is_inference:
			predictions = torch.argmax(logits, dim=-1)
			all_predictions.extend(predictions.cpu().numpy())
			# 收集当前batch的文件路径信息
			batch_start_idx = step * config.data.batch_size
			for i in range(len(predictions)):
				sample_idx = batch_start_idx + i
				if sample_idx < len(test_loader.dataset):
					sample_path = test_loader.dataset.samples[sample_idx][0]
					rel_path = extract_relative_path(sample_path, config.data.dataset)
					all_paths.append(rel_path)

		if save_feature:
			saved_feature.append(logits)
			saved_labels.append(y)
		
		# 推理模式下跳过损失和精度计算（因为测试集标签为-1占位符）
		if is_inference:
			# 推理模式下设置虚拟值，避免progress bar显示错误
			loss_value = 0.0
			acc_value = 0.0
		else:
			# 训练/验证模式下正常计算损失和精度
			loss = criterion(logits, y.long())
			acc = accuracy(logits, y)[0]
			if config.local_rank != -1:
				acc = reduce_mean(acc)
			loss_value = loss.item()
			acc_value = acc.item()

		loss_meter.update(loss_value, y.size(0))
		acc_meter.update(acc_value, y.size(0))

		p_bar.set_postfix(acc="{:2.3f}".format(acc_meter.avg), loss="%2.5f" % loss_meter.avg,
		                  tra="{:2.3f}".format(train_acc * 100))
		p_bar.update()
		pass
	if save_feature:
		os.makedirs('visualize/saved_features',exist_ok=True)
		saved_feature = torch.cat(saved_feature, 0)
		saved_labels = torch.cat(saved_labels,0)
		torch.save(saved_feature,f'visualize/saved_features/{config.data.dataset}_f.pth')
		torch.save(saved_labels, f'visualize/saved_features/{config.data.dataset}_l.pth')
	p_bar.close()
	
	# 推理模式下保存预测结果
	if is_inference and hasattr(config.inference, 'save_predictions') and config.inference.save_predictions:
		save_predictions_to_file(all_paths, all_predictions, config)
		
	if writer:
		writer.add_scalar("test/accuracy", acc_meter.avg, epoch + 1)
		writer.add_scalar("test/loss", loss_meter.avg, epoch + 1)
		writer.add_scalar("test/train_acc", train_acc * 100, epoch + 1)
	return acc_meter.avg, loss_meter.avg


@torch.no_grad()
def throughput(data_loader, model, log, rank):
	model.eval()
	for idx, (images, _) in enumerate(data_loader):
		images = images.cuda(non_blocking=True)
		batch_size = images.shape[0]
		for i in range(50):
			model(images)
		torch.cuda.synchronize()
		if rank in [-1, 0]:
			log.info(f"throughput averaged with 30 times")
		tic1 = time.time()
		for i in range(30):
			model(images)
		torch.cuda.synchronize()
		tic2 = time.time()
		if rank in [-1, 0]:
			log.info(f"batch_size {batch_size} throughput {30 * batch_size / (tic2 - tic1)}")
		return


if __name__ == '__main__':
	main(config)
