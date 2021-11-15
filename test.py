from DeamNet import Deam
import os
import argparse
import numpy as np
from skimage import img_as_ubyte
from model import DGNet
from tqdm import tqdm
from scipy.io import loadmat, savemat
import torch

os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
parser = argparse.ArgumentParser()
parser.add_argument('--pretrained', type=str, default='./Deam_models/', help="Checkpoints directory,  (default:./checkpoints)")
parser.add_argument('--Isreal', default=True, help='Location to save checkpoint models')
parser.add_argument('--data_folder', type=str, default='./Dataset/test', help='Location to save checkpoint models')
parser.add_argument('--out_folder', type=str, default='./Dnd_result', help='Location to save checkpoint models')
parser.add_argument('--model', type=str, default='Real.pth', help='Location to save checkpoint models')
parser.add_argument('--Type', type=str, default='SIDD', help='To choose the testing benchmark dataset, SIDD or Dnd')
args = parser.parse_args()
use_gpu = True

print('Loading the Model')
net = DGNet(args.Isreal)
checkpoint = torch.load(os.path.join(args.pretrained, args.model))
model = torch.nn.DataParallel(net).cuda()
model.eval()


def denoise(model, noisy_image):
    with torch.autograd.set_grad_enabled(False):
        torch.cuda.synchronize()

        phi_Z = model(noisy_image)
        torch.cuda.synchronize()
        im_denoise = phi_Z.cpu().numpy()

    im_denoise = np.transpose(im_denoise.squeeze(), (1, 2, 0))
    im_denoise = img_as_ubyte(im_denoise.clip(0, 1))

    return im_denoise


def test(args):
    use_gpu = True
    # load the pretrained model
    print('Loading the Model')
    # args = parse_benchmark_processing_arguments()
    checkpoint = torch.load(os.path.join(args.pretrained, args.model))
    net = DGNet(args.Isreal)
    if use_gpu:
        net = torch.nn.DataParallel(net).cuda()
        net.load_state_dict(checkpoint)
    net.eval()

    # load SIDD benchmark dataset and information
    noisy_data_mat_file = os.path.join(args.data_folder, 'SIDD', 'BenchmarkNoisyBlocksSrgb.mat')
    noisy_data_mat_name = os.path.basename(noisy_data_mat_file).replace('.mat', '')
    noisy_data_mat = loadmat(noisy_data_mat_file)[noisy_data_mat_name]

    npose = (noisy_data_mat.shape[0])
    nsmile = noisy_data_mat.shape[1]
    poseSmile_cell = np.empty((npose, nsmile), dtype=object)

    for image_index in tqdm(range(noisy_data_mat.shape[0])):
        for block_index in range(noisy_data_mat.shape[1]):
            noisy_image = noisy_data_mat[image_index, block_index, :, :, :]
            noisy_image = np.float32(noisy_image / 255.)
            noisy_image = torch.from_numpy(noisy_image.transpose((2, 0, 1))[np.newaxis, ])
            poseSmile_cell[image_index, block_index] = denoise(net, noisy_image)

    submit_data = {
            'DenoisedBlocksSrgb': poseSmile_cell
        }

    savemat(
            os.path.join(os.path.dirname(noisy_data_mat_file), 'SubmitSrgb.mat'),
            submit_data
        )