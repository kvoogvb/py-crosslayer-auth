from torch import nn
from torch.nn import functional as F
from collections import OrderedDict



# structure = [(32,64,2),(64,128,2),(128,256,2)] #v2_ok.pth
# structure = [(32,64,2),(64,128,2)] #v3_ok.pth
# structure = [(32,64,2)] #v4_ok.pth
structure = [(64,64,1)] #v5_ok.pth

id = 0
class Residual(nn.Module):
    def __init__(self, ci,co,bottleneck=False,stride=1, **kwargs):
        super().__init__(**kwargs)
        # global id
        self.transinput = False
        self.bottleneck = bottleneck

        if co != ci or stride!=1:
            self.conv0 = nn.Conv1d(ci,co,kernel_size=1,stride=stride)
            self.transinput = True
        
        self.conv1 = nn.Conv1d(ci,co,kernel_size=3,padding=1,stride=stride)
        self.bn2 = nn.BatchNorm1d(co)
        self.conv3 = nn.Conv1d(co,co,kernel_size=3,padding=1)
        self.bn4 = nn.BatchNorm1d(co)
    
    def forward(self,X):
        Y = F.relu(self.bn2(self.conv1(X)))
        Y = self.bn4(self.conv3(Y))

        if self.transinput:
            X = self.conv0(X)
        Y += X
        return F.relu(Y)
    

def resnet_block(pre_co,co,num,keepsize=False):
    global id
    blk = []
    stride=1
    if not keepsize:
        stride = 2

    for i in range(num):
        if i == 0:
            blk.append((f'Residual-{id}',Residual(pre_co,co,stride=stride)))
            id+=1
        else:
            blk.append((f'Residual-{id}',Residual(co,co)))
            id+=1
    return OrderedDict(blk)

def getnet(adjust=False,keepsize=None):

    co_init=structure[0][0]
    net = nn.Sequential(
        nn.Conv1d(1,co_init,kernel_size=7,stride=2,padding=3),nn.BatchNorm1d(co_init),nn.ReLU(),
    )

    flag=1
    pre_co=co_init
    for (ci,co,num) in structure:
        if flag:
            net.append(
                nn.Sequential(resnet_block(pre_co,co,num,keepsize=True))
            )
            flag=0
            pre_co=co
            continue
        net.append(
            nn.Sequential(resnet_block(pre_co,co,num,ci))
        )
        pre_co=co

    net.append(nn.Sequential(
        nn.AdaptiveAvgPool1d(1),nn.Flatten(),
        # nn.Dropout(0.5),
        nn.Linear(pre_co,6)
    ))
    return net

# net = getnet()
# print(net)
# data = torch.rand((1,1,222))
# print(data)
# res = net(data)
# print(res)
