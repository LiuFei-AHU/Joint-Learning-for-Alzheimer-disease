from options.base_options import BaseOptions


class TrainOptions(BaseOptions):
    def initialize(self, parser):
        parser = BaseOptions.initialize(self, parser)
        parser.add_argument('--print_freq', type=int, default=1,
                            help='frequency of showing training results on console')
        parser.add_argument('--seed', type=int, default=43,
                            help='random seed')
        parser.add_argument('--update_step', type=int, default=4,
                            help='virtual batch size = real batch size * update_step')
        parser.add_argument('--save_latest_freq', type=int, default=50, help='frequency of saving the latest results')
        parser.add_argument('--save_epoch_freq', type=int, default=20,
                            help='frequency of saving checkpoints at the end of epochs')
        parser.add_argument('--eval_freq', type=int, default=1,
                            help='frequency of eval the model at the end of epochs')
        parser.add_argument('--patience', type=int, default=5,
                            help='How long to wait after last time validation loss improved.')

        parser.add_argument('--continue_train', action='store_true', help='continue training: load the latest model')
        parser.add_argument('--phase', type=str, default='train', help='train, val, test, etc')
        parser.add_argument('--which_epoch', type=str, default='latest',
                            help='which epoch to load? set to latest to use latest cached model')
        parser.add_argument('--epoch_count', type=int, default=0,
                            help='the starting epoch count, we save the model by <epoch_count>, <epoch_count>+<save_latest_freq>, ...')
        parser.add_argument('--niter', type=int, default=30, help='# of iter at starting learning rate')
        parser.add_argument('--niter_decay', type=int, default=50,
                            help='# of iter to linearly decay learning rate to zero')
        parser.add_argument('--lr_num', type=float, default=0.9, help='learning rate of num expotention')
        parser.add_argument('--beta1', type=float, default=0.5, help='momentum term of adam')
        parser.add_argument('--lr', type=float, default=0.0002, help='initial learning rate for cyclegenerator adam')
        parser.add_argument('--lr_G', type=float, default=0.0002, help='initial learning rate for generator adam')
        parser.add_argument('--lr_D', type=float, default=0.0001, help='initial learning rate for discriminator adam')
        parser.add_argument('--no_lsgan', action='store_true',
                            help='do *not* use least square GAN, if false, use vanilla GAN')
        parser.add_argument('--pool_size', type=int, default=10,
                            help='the size of image buffer that stores previously generated images')
        parser.add_argument('--lr_policy', type=str, default='step',
                            help='learning rate policy: lambda|step|plateau|cosine')
        parser.add_argument('--lr_decay_iters', type=int, default=50,
                            help='multiply by a gamma every lr_decay_iters iterations')

        self.isTrain = True
        return parser
