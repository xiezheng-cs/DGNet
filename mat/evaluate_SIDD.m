close all;clear all;

denoised = load('denoised.mat');
gt = load('clean.mat');

denoised = denoised.denoised;
gt = gt.clean;
gt = im2single(gt);

total_psnr = 0;
total_ssim = 0;
for i = 1:len(denoised)
   denoised_patch = squeeze(denoised(i,:,:,:));
   gt_patch = squeeze(gt(i,:,:,:));
   ssim_val = ssim(denoised_patch, gt_patch);
   psnr_val = psnr(denoised_patch, gt_patch);
   total_ssim = total_ssim + ssim_val;
   total_psnr = total_psnr + psnr_val;
end
qm_psnr = total_psnr / (40*32);
qm_ssim = total_ssim / (40*32);

fprintf('PSNR: %f SSIM: %f\n', qm_psnr, qm_ssim);

