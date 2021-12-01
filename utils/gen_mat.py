import os
import numpy as np
import torch
import scipy.io as sio
from utils.util import *
from utils.checkpoint import *


def gen_mat(model, pretrain_model, dst_path, data_loader, batch_size, patch_size, logger):
    model, psnr_best = load_single_model(pretrain_model, model, logger)
    model.cuda()
    model.eval()
    store_data_prediction = np.zeros((len(data_loader) * batch_size, patch_size, patch_size, 3), float)
    store_data_clean = np.zeros((len(data_loader) * batch_size, patch_size, patch_size, 3), float)

    num = 0
    for iteration, (noisy, target) in enumerate(data_loader):
        noisy, target = noisy.cuda(), target.cuda()
        with torch.no_grad():
            prediction = model(noisy)
            prediction = prediction.data.cpu().permute(0, 2, 3, 1).numpy().astype(np.float32)
            target = target.data.cpu().permute(0, 2, 3, 1).numpy().astype(np.float32)
            for i in range(prediction.shape[0]):
                store_data_prediction[iteration * prediction.shape[0] + i, :, :, :] = prediction[i]
                store_data_clean[iteration * prediction.shape[0] + i, :, :, :] = target[i]
                num += 1

    store_data_clean.resize((num, patch_size, patch_size, 3))
    store_data_prediction.resize((num, patch_size, patch_size, 3))
    sio.savemat(os.path.join(dst_path, 'denoised.evaluate_mat'), {"denoised": store_data_prediction})
    sio.savemat(os.path.join(dst_path, 'clean.evaluate_mat'), {"clean": store_data_clean})
    logger.info('Mat with best model and {} patches generated!'.format(num))
