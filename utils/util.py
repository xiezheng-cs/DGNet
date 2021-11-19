import os
import sys
import logging
import numpy as np
import torch
import glob
from natsort import natsorted
from collections import OrderedDict
from skimage.measure import compare_psnr, compare_ssim


def mkdir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


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
    logger.info(net)
    logger.info('Total number of parameters: {}'.format(num_params))


def get_last_path(path, session):
    x = natsorted(glob.glob(os.path.join(path, '*{}'.format(session))))[-1]
    return x


def load_optim(optimizer, weights):
    checkpoint = torch.load(weights)
    optimizer.load_state_dict(checkpoint['optimizer'])


def load_start_epoch(weights):
    checkpoint = torch.load(weights)
    epoch = checkpoint["epoch"]
    return epoch


def load_checkpoint(model, weights):
    checkpoint = torch.load(weights)
    try:
        model.load_state_dict(checkpoint["state_dict"])
    except:
        state_dict = checkpoint["state_dict"]
        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            name = k[7:] # remove `module.`
            new_state_dict[name] = v
        model.load_state_dict(new_state_dict)


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
