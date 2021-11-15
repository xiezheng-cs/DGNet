from __future__ import print_function
import os
import time
import socket
import pandas as pd
import argparse
import torch.nn as nn
import torch.optim as optim
import torch.backends.cudnn as cudnn
from torch.utils.data import DataLoader
from model import DGNet
from skimage.measure.simple_metrics import compare_psnr
from dataloader import *
from utils.util import get_logger

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"

# Training settings
parser = argparse.ArgumentParser(description='PyTorch Super Res Example')
parser.add_argument('--upscale_factor', type=int, default=1, help="super resolution upscale factor")
parser.add_argument('--batch_size', type=int, default=8, help='training batch size')
parser.add_argument('--nEpochs', type=int, default=2000, help='number of epochs to train for')
parser.add_argument('--start_iter', type=int, default=1, help='starting epoch')
parser.add_argument('--lr', type=float, default=0.0001, help='learning rate. default=0.0001')
parser.add_argument('--data_augmentation', type=bool, default=True, help='if adopt augmentation when training')
parser.add_argument('--hr_train_dataset', type=str, default='DIV2K_train_HR', help='the training dataset')
parser.add_argument('--Ispretrained', type=bool, default=False, help='If load checkpoint model')
parser.add_argument('--pretrained_sr', default='noise25.pth', help='sr pretrained base model')
parser.add_argument('--pretrained', default='./Deam_models', help='Location to load checkpoint models')
parser.add_argument("--noiseL", type=float, default=25, help='noise level')
parser.add_argument('--save_folder', default='./checkpoint/', help='Location to save checkpoint models')
parser.add_argument('--statistics', default='./statistics/', help='Location to save statistics')

# Testing settings
parser.add_argument('--test_batch_size', type=int, default=1, help='testing batch size, default=1')
parser.add_argument('--seed', type=int, default=123, help='random seed to use. Default=123')
parser.add_argument('--test_dataset', type=str, default='Set12', help='the testing dataset')
parser.add_argument("--val_noiseL", type=float, default=25, help='noise level used on validation set')

# Global settings
parser.add_argument('--threads', type=int, default=4, help='number of threads for data loader to use')
parser.add_argument('--gpus', default=1, type=int, help='number of gpus')
parser.add_argument('--data_dir', type=str, default='./Dataset', help='the dataset dir')
parser.add_argument('--model_type', type=str, default='DGNet', help='the name of model')
parser.add_argument('--patch_size', type=int, default=150, help='Size of cropped HR image')


opt = parser.parse_args()
gpus_list = range(opt.gpus)
hostname = str(socket.gethostname())
cudnn.benchmark = True


def train(epoch):
    epoch_loss = 0
    model.train()
    for iteration, batch in enumerate(training_data_loader, 0):
        target = batch[1]
        input = batch[0]

        input = input.cuda()
        target = target.cuda()

        model.zero_grad()
        optimizer.zero_grad()
        t0 = time.time()

        prediction = model(input)

        # Corresponds to the Optimized Scheme
        loss = criterion(prediction, target)/(input.size()[0]*2)

        t1 = time.time()
        epoch_loss += loss.data
        loss.backward()
        optimizer.step()

        if (iteration+1) % 50 == 0:
            model.eval()
            SC = 'net_epoch_' + str(epoch) + '_' + str(iteration + 1) + '.pth'
            torch.save(model.state_dict(), os.path.join(opt.save_folder, SC))
            model.train()

        logger.info("===> Epoch[{}]({}/{}): Loss: {:.4f} || Timer: {:.4f} sec.".format(epoch, iteration, len(training_data_loader), loss.data, (t1 - t0)))
    logger.info("===> Epoch {} Complete: Avg. Loss: {:.4f}".format(epoch, epoch_loss / len(training_data_loader)))


def batch_PSNR(img, imclean, data_range):
    Img = img.data.cpu().numpy().astype(np.float32)
    Iclean = imclean.data.cpu().numpy().astype(np.float32)
    PSNR = 0
    for i in range(Img.shape[0]):
        PSNR += compare_psnr(Iclean[i, :, :, :], Img[i, :, :, :], data_range=data_range)
    return (PSNR / Img.shape[0])


def test(noisy, clean):
    psnr_test= 0
    model.eval()
    for iteration, batch in enumerate(noisy, 0):
        target = batch[1]
        input = batch[0]

        input = input.cuda()
        target = target.cuda()
        with torch.no_grad():
            prediction = model(input)
            prediction = torch.clamp(prediction, 0., 1.)
        psnr_test += batch_PSNR(prediction, target, 1.)
    logger.info("===> Avg. PSNR: {:.4f} dB".format(psnr_test / len(noisy)))
    return psnr_test / len(noisy)


def print_network(net):
    num_params = 0
    for param in net.parameters():
        num_params += param.numel()
    logger.info(net)
    logger.info('Total number of parameters: %d' % num_params)


def checkpoint(epoch, psnr):
    model_out_path = opt.save_folder+hostname+opt.model_type+"_psnr_{}".format(psnr)+"_epoch_{}.pth".format(epoch)
    torch.save(model.state_dict(), model_out_path)
    logger.info("Checkpoint saved to {}".format(model_out_path))


if __name__ == '__main__':
    logger = get_logger(opt.save_folder, 'DGNet_log')
    logger.info(opt)
    logger.info('===>Loading datasets')

    train_set = Dataset_h5_real(src_path=os.path.join(opt.data_dir, 'train', 'train.h5'), patch_size=opt.patch_size, train=True)
    training_data_loader = DataLoader(dataset=train_set, batch_size=opt.batch_size, shuffle=True, num_workers=4, drop_last=True)

    test_set = Dataset_h5_real(src_path=os.path.join(opt.data_dir, 'test', 'val.h5'), patch_size=opt.patch_size, train=False)
    testing_data_loader = DataLoader(dataset=test_set, batch_size=opt.test_batch_size, shuffle=False, num_workers=0, drop_last=True)


    logger.info('===> Loading datasets{}'.format(opt.model_type))
    logger.info('===> Building model ', opt.model_type)
    model = DGNet()

    model = torch.nn.DataParallel(model, device_ids=gpus_list)
    criterion = nn.MSELoss()

    logger.info('---------- Networks architecture -------------')
    print_network(model)
    logger.info('----------------------------------------------')

    optimizer = optim.Adam(model.parameters(), lr=opt.lr, betas=(0.9, 0.999), eps=1e-8)

    PSNR = []
    for epoch in range(opt.start_iter, opt.nEpochs + 1):
        train(epoch)
        psnr = test(testing_data_loader, testing_data_loader)
        PSNR.append(psnr)
        data_frame = pd.DataFrame(
            data={'epoch': epoch, 'PSNR': PSNR}, index=range(1, epoch+1)
        )
        data_frame.to_csv(os.path.join(opt.statistics, 'training_logs.csv'), index_label='index')
        # learning rate is decayed by a factor of 10 every half of total epochs
        if (epoch + 1) % (opt.nEpochs / 2) == 0:
            for param_group in optimizer.param_groups:
                param_group['lr'] /= 10.0
                logger.info('Learning rate decay: lr={}'.format(param_group['lr']))
