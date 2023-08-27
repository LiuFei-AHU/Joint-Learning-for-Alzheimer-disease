python ../../Frame_train.py \
--gpu_ids 0,4 \
--update_step 2 \
--lambda_A 10 \
--lambda_B 10 \
--model joint_gan \
--name joint_framework \
--checkpoints_dir /data/chwang/Log/JointFrame \
--lambda_identity 0. \
--lambda_cls_A 1. \
--lambda_cls_B 1. \
--batch_size 1 \
--eval_freq 200 \
--use_earlystop \
--patience 5 \
--workers 2 \
--load_size 256 \
--crop_size 256 \
--netG ShareSynNet \
--netD Defined \
--ndf 64 \
--n_layers_D 5 \
--init_type kaiming \
--lr_G 0.00001 \
--lr_D 0.000001 \
--beta1 0.5 \
--norm instance \
--lr_policy lambda \
--lr_num 0.7 \
--epoch_count 1 \
--niter 0 \
--niter_decay 15 \
--save_epoch_freq 1 \
--save_latest_freq 400 \
--pool_size 1 \
--continue_train \
--which_epoch pretrained \
--usejoint