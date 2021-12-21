import os
import sys
import logging
import torch
import glob
from collections import OrderedDict
import shutil
import torch.distributed as dist


def ddp_logger_info(output, logger, local_rank):
    if local_rank == 0:
        logger.info(output)


def ddp_writer_add_scalar(label, data, epoch, writer, local_rank):
    if local_rank == 0:
        writer.add_scalar(label, data, epoch)


def make_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def output_process(output_path):
    if os.path.exists(output_path):
        print("{} file exist!".format(output_path))
        raise OSError("Directory {} exits!".format(output_path))

    if not os.path.exists(output_path):
        os.makedirs(output_path)


def get_logger(save_path, logger_name):
    logger = logging.getLogger(logger_name)
    file_formatter = logging.Formatter('%(asctime)s: %(message)s')
    console_formatter = logging.Formatter('%(message)s')

    # file log
    file_handler = logging.FileHandler(os.path.join(save_path, "experiment.log"))
    file_handler.setFormatter(file_formatter)

    # console log
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.setLevel(logging.INFO)
    return logger


def print_network(net, logger):
    num_params = 0
    for param in net.parameters():
        num_params += param.numel()
    logger.info('model={}'.format(net))
    logger.info('Total number of parameters: {}'.format(num_params))


def reduce_mean(tensor, nprocs):
    rt = tensor.clone()
    dist.all_reduce(rt, op=dist.ReduceOp.SUM)
    rt /= nprocs
    return rt


def dataset_sort(data_loader_1, data_loader_2, data_loader_3):
    len1 = len(data_loader_1)
    len2 = len(data_loader_2)
    len3 = len(data_loader_3)
    max_len = max(len1, len2, len3)
    if len3 == max_len:
        return data_loader_1, data_loader_2, data_loader_3
    elif len2 == max_len:
        return data_loader_1, data_loader_3, data_loader_2
    elif len1 == max_len:
        return data_loader_2, data_loader_3, data_loader_1


def register_hook(model, hook_layers, func):
    for name, layer in model.named_modules():
        if name in hook_layers:
            layer.register_forward_hook(func)


def accuracy(scores, targets, k=1):
    batch_size = targets.size(0)
    _, ind = scores.topk(k, 1, True, True)
    correct = ind.eq(targets.long().view(-1, 1).expand_as(ind))
    correct_total = correct.view(-1).float().sum()  # 0D tensor
    return correct_total.item() * (1.0 / batch_size)


class AverageMeter(object):
    def __init__(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count
