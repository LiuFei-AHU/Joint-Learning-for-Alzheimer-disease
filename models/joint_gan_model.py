import itertools
import random

from components import networks3D
from components.losses import *
from .base_model import BaseModel


class ImagePool():
    def __init__(self, pool_size):
        self.pool_size = pool_size
        if self.pool_size > 0:
            self.num_imgs = 0
            self.images = []

    def query(self, images):
        if self.pool_size == 0:
            return images
        return_images = []
        for image in images:
            image = torch.unsqueeze(image.data, 0)
            if self.num_imgs < self.pool_size:
                self.num_imgs = self.num_imgs + 1
                self.images.append(image)
                return_images.append(image)
            else:
                p = random.uniform(0, 1)
                if p > 0.5:
                    random_id = random.randint(0, self.pool_size - 1)  # randint is inclusive
                    tmp = self.images[random_id].clone()
                    self.images[random_id] = image
                    return_images.append(tmp)
                else:
                    return_images.append(image)
        return_images = torch.cat(return_images, 0)
        return return_images


class JointGANModel(BaseModel):
    def name(self):
        return 'JointGANModel'

    @staticmethod
    def modify_commandline_options(parser, is_train=True):
        parser.set_defaults(no_dropout=True)
        if is_train:
            parser.add_argument('--lambda_A', type=float, default=10.0, help='weight for cycle loss (A -> B -> A)')
            parser.add_argument('--lambda_B', type=float, default=10.0,
                                help='weight for cycle loss (B -> A -> B)')
            parser.add_argument('--lambda_identity', type=float, default=0.5,
                                help='use identity mapping. Setting lambda_identity other than 0 has an effect of '
                                     'scaling the weight of the identity mapping loss. For example, if the weight of the'
                                     ' identity loss should be 10 times smaller than the weight of the reconstruction loss, '
                                     'please set lambda_identity = 0.1')
            '''
            end-to-end classifier
            '''
            parser.add_argument('--lambda_cls_A', type=float, default=0., help='weight for classifier_loss _A')
            parser.add_argument('--lambda_cls_B', type=float, default=0., help='weight for classifier_loss _B')
            parser.add_argument('--class_num', type=int, default=2,
                                help='the number of class')

        return parser

    def initialize(self, opt):
        BaseModel.initialize(self, opt)

        # specify the training losses you want to print out. The program will call base_model.get_current_losses
        self.loss_names = ['G', 'Gen', 'Cls', 'D_A', 'G_A', 'cycle_A', 'idt_A', 'D_B', 'G_B',
                           'cycle_B', 'idt_B']
        # , 'Cls_A', 'Cls_B'
        # specify the images you want to save/display. The program will call base_model.get_current_visuals
        visual_names_A = ['real_A', 'fake_B', 'rec_A']
        visual_names_B = ['real_B', 'fake_A', 'rec_B']
        if self.isTrain and self.opt.lambda_identity > 0.0:
            visual_names_A.append('idt_A')
            visual_names_B.append('idt_B')

        self.visual_names = visual_names_A + visual_names_B
        # specify the models you want to save to the disk. The program will call base_model.save_networks and base_model.load_networks
        if self.isTrain:
            self.model_names = ['G', 'D_A', 'D_B', 'Cls']
        else:  # during test time, only load Gs
            self.model_names = ['G', 'Cls']

        # load/define networks
        # The naming conversion is different from those used in the paper
        self.netG = networks3D.define_G(opt.input_nc, opt.output_nc, opt.ngf, opt.netG, opt.norm,
                                        not opt.no_dropout, opt.init_type, opt.init_gain, self.gpu_ids,
                                        opt.usejoint).to('cuda:0')

        # end2end classifier
        self.netCls = networks3D.define_Cls(
            opt.class_num, opt.init_type, opt.init_gain, self.gpu_ids, opt.usejoint).to('cuda:1')

        if self.isTrain:
            use_sigmoid = opt.no_lsgan
            self.netD_A = networks3D.define_D(opt.output_nc, opt.ndf, opt.netD,
                                              opt.n_layers_D, opt.norm, use_sigmoid, opt.init_type, opt.init_gain,
                                              self.gpu_ids, opt.usejoint).to('cuda:0')
            self.netD_B = networks3D.define_D(opt.input_nc, opt.ndf, opt.netD,
                                              opt.n_layers_D, opt.norm, use_sigmoid, opt.init_type, opt.init_gain,
                                              self.gpu_ids, opt.usejoint).to('cuda:0')

        if self.isTrain:
            self.fake_A_pool = ImagePool(opt.pool_size)
            self.fake_B_pool = ImagePool(opt.pool_size)
            # define loss functions
            self.criterionGAN = GANLoss(gpu_ids=self.gpu_ids, use_lsgan=not opt.no_lsgan)
            self.criterionCycle = torch.nn.L1Loss()
            self.criterionIdt = torch.nn.L1Loss()
            self.criterionClassifier = torch.nn.CrossEntropyLoss()

            # initialize optimizers
            self.optimizer_G = torch.optim.Adam(
                [{'params': self.netG.parameters(), 'lr': opt.lr_G * 0.1},
                 {'params': self.netCls.parameters(), 'lr': opt.lr_G}],
                betas=(opt.beta1, 0.999))
            self.optimizer_D = torch.optim.Adam(itertools.chain(self.netD_A.parameters(), self.netD_B.parameters()),
                                                lr=opt.lr_D, betas=(opt.beta1, 0.999))
            self.optimizers = []
            self.optimizers.append(self.optimizer_G)
            self.optimizers.append(self.optimizer_D)

    def set_input(self, input):
        AtoB = self.opt.which_direction == 'AtoB'
        self.real_A = input[0 if AtoB else 1].to('cuda:0')
        self.real_B = input[1 if AtoB else 0].to('cuda:0')
        self.real_label = input[2].to('cuda:1')

    def forward(self):
        self.fake_B = self.netG(self.real_A, alpha=0.0)
        self.rec_A = self.netG(self.fake_B, alpha=1.0)
        self.fake_A = self.netG(self.real_B, alpha=1.0)
        self.rec_B = self.netG(self.fake_A, alpha=0.0)

        self.label_A, _, _, _, _ = self.netCls(self.real_A.squeeze(1).to('cuda:1'))
        self.label_B, _, _, _, _ = self.netCls(self.fake_B.squeeze(1).to('cuda:1'))

    def backward_D_basic(self, netD, real, fake, update_step=1.):
        # Real
        pred_real = netD(real)
        loss_D_real = self.criterionGAN(pred_real, True)
        # Fake
        pred_fake = netD(fake.detach())
        loss_D_fake = self.criterionGAN(pred_fake, False)
        # Combined loss
        loss_D = ((loss_D_real + loss_D_fake) * 0.5) / update_step
        # backward
        loss_D.backward()
        return loss_D

    def backward_D_A(self, update_step=1.):
        fake_B = self.fake_B_pool.query(self.fake_B)
        self.loss_D_A = self.backward_D_basic(self.netD_A, self.real_B, fake_B, update_step)

    def backward_D_B(self, update_step):
        fake_A = self.fake_A_pool.query(self.fake_A)
        self.loss_D_B = self.backward_D_basic(self.netD_B, self.real_A, fake_A, update_step)

    def backward_G(self, update_step=1.):
        lambda_idt = self.opt.lambda_identity
        lambda_A = self.opt.lambda_A
        lambda_B = self.opt.lambda_B
        lambda_cls_A = self.opt.lambda_cls_A
        lambda_cls_B = self.opt.lambda_cls_B
        '''
        identity loss 
        '''
        if lambda_idt > 0:
            self.idt_A = self.netG(self.real_B, alpha=0.0)
            self.idt_B = self.netG(self.real_A, alpha=1.0)
            # G_A should be identity if real_B is fed.
            self.loss_idt_A = self.criterionIdt(self.idt_A, self.real_B) * lambda_B * lambda_idt
            # G_B should be identity if real_A is fed.
            self.loss_idt_B = self.criterionIdt(self.idt_B, self.real_A) * lambda_A * lambda_idt
        else:
            self.loss_idt_A = 0.
            self.loss_idt_B = 0.
        '''
        GAN loss
        '''
        # GAN loss D_A(G_A(A))
        self.loss_G_A = self.criterionGAN(self.netD_A(self.fake_B), True)
        # GAN loss D_B(G_B(B))
        self.loss_G_B = self.criterionGAN(self.netD_B(self.fake_A), True)
        '''
        Cycle loss
        '''
        # Forward cycle loss
        self.loss_cycle_A = (self.criterionCycle(self.rec_A, self.real_A)) * lambda_A
        # Backward cycle loss
        self.loss_cycle_B = (self.criterionCycle(self.rec_B, self.real_B)) * lambda_B
        '''
        classification loss
        '''
        #######################################     【random type】     #################################################
        # uniform distribution for [0,1)
        random_num = random.random()
        if random_num >= 0.5:
            self.loss_Cls = (self.criterionClassifier(self.label_A, self.real_label) * lambda_cls_A) / update_step
        else:
            self.loss_Cls = (self.criterionClassifier(self.label_B, self.real_label) * lambda_cls_B) / update_step
        ################################################################################################################
        # combined loss
        self.loss_Gen = (self.loss_G_A + self.loss_G_B + self.loss_cycle_A + self.loss_cycle_B +
                         self.loss_idt_A + self.loss_idt_B) / update_step

        self.loss_G = self.loss_Gen.to('cuda:1') + self.loss_Cls
        self.loss_G.backward()

    def optimize_parameters(self, update_step=1., upgate=True):
        # forward
        self.forward()
        # G_A and G_B
        self.set_requires_grad([self.netD_A, self.netD_B], False)
        self.backward_G(update_step)
        if upgate:
            self.optimizer_G.step()
            self.optimizer_G.zero_grad()
        # D_A and D_B
        self.set_requires_grad([self.netD_A, self.netD_B], True)
        self.backward_D_A(update_step)
        self.backward_D_B(update_step)
        if upgate:
            self.optimizer_D.step()
            self.optimizer_D.zero_grad()
        # torch.cuda.empty_cache()
