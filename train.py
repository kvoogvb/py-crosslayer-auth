import math
import torch
from torch import nn
from d2l import torch as d2l
from torch.utils.tensorboard import SummaryWriter
from datetime import datetime
from torch.optim import lr_scheduler
from torch.amp import autocast, GradScaler
from dataloader import get_dataloader
from model import getnet

def load_model(net,path):
    checkpoint = torch.load(path)
    model_dict = net.state_dict()
    pretrained_dict = {k: v for k, v in checkpoint['model_state_dict'].items() 
            if k in model_dict and v.shape == model_dict[k].shape}
    model_dict.update(pretrained_dict)
    net.load_state_dict(model_dict,strict=False)
    return net

def save_paramter(net,optimizer):
    save = input("press y if want to save: ")
    checkpoint=None
    if save == "y":
        save = input("save file name: ")
        checkpoint = {
        'model_state_dict': net.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        }
        torch.save(checkpoint, f'{save}.pth')

def clear_line():
    """清除当前行"""
    print('\r\033[K', end='', flush=True)

def cal_test(net,data_iter,loss,device,cal_acc=True):
    test_loss,test_acc,samples = 0,0,0
    net.eval()
    with torch.no_grad():
        for X,y in data_iter:
            if isinstance(X, list):
                # Required for BERT Fine-tuning (to be covered later)
                X = [x.to(device) for x in X]
            else:
                X = X.to(device)
            y = y.to(device)
            y_hat = net(X)
            l = loss(y_hat,y)
            test_loss += l*X.shape[0]
            if cal_acc:
                test_acc += d2l.accuracy(y_hat,y)
            samples += X.shape[0]
    return test_acc/samples,test_loss/samples

def soft_cross_entropy(y_hat,y):
    log_probs = torch.log_softmax(y_hat, dim=1)
    #only use when mix up,mixup give one hot key y
    return torch.mean(torch.sum(-y * log_probs, dim=1))

def trainer(net, train_iter, test_iter, num_epochs, lr,device,writer,momentum=0,wd=0,
            optimizer = None,loss = nn.CrossEntropyLoss(),mixup=False,scheduler=None):
    if optimizer == None:
        optimizer = torch.optim.Adam(params=net.parameters(),lr=lr,weight_decay=wd)
    # if opt == 'sgd':
    #     optimizer = torch.optim.SGD(params=net.parameters(),lr=lr,weight_decay=wd,momentum=momentum)

    return train(net, train_iter, test_iter, num_epochs,device,writer,opt = optimizer,loss=loss,mixup=mixup,scheduler=scheduler)

def train(net, train_iter, test_iter, num_epochs,device,writer,opt,loss= nn.CrossEntropyLoss(),scheduler=None):

    print("training on",device)
    print("0 % epochs done")
    print("done 0 % of an epoch")
    net = net.to(device)
    # opt.to(device)
    timer, num_batches = d2l.Timer(), len(train_iter)
    # if mixup:
    #     # loss = nn.KLDivLoss(reduction='batchmean')
    #     loss = soft_cross_entropy()


    with open('temlog.txt', 'w', encoding='utf-8') as file:
        file.write(datetime.now().strftime("%m月%d日%H;%M;%S")+"\n")

    cnt = 10
    scaler = GradScaler()
    for epoch in range(num_epochs):
        metric = d2l.Accumulator(3)
        net.train()
        samples = 5
        for i,(X,y) in enumerate(train_iter):
            timer.start()
            opt.zero_grad()
            X,y = X.to(device),y.to(device)
            with autocast(device_type='cuda'):
                y_hat = net(X)
                l = loss(y_hat,y)
            scaler.scale(l).backward()
            scaler.unscale_(opt)
            nn.utils.clip_grad_norm_(net.parameters(),1.0)
            scaler.step(opt)
            scaler.update()
            # l.backward()
            # opt.step()
            with torch.no_grad():
                metric.add(l * X.shape[0], d2l.accuracy(y_hat, y), X.shape[0])
            timer.stop()
            train_l = metric[0] / metric[2]
            train_acc = metric[1] / metric[2]
            if (i + 1) % (num_batches // 3) == 0 or i == num_batches - 1:
                writer.add_scalar("Train_loss",train_l,epoch+(i+1)/num_batches)
                writer.add_scalar("Train_acc",train_acc,epoch+(i+1)/num_batches)
            
            if samples <= (i+1)*100.0/num_batches:
                print("\033[F",end='',flush=True)
                clear_line()
                print("done",samples,"% of an epoch")
                samples+=5

        # test_acc = d2l.evaluate_accuracy_gpu(net, test_iter,device=device)
        test_acc,test_l = cal_test(net,test_iter,nn.CrossEntropyLoss(),device)
        writer.add_scalar("Test_acc",test_acc,epoch)
        writer.add_scalar("Test_loss",test_l,epoch)

        with open('temlog.txt', 'a', encoding='utf-8') as file:
            file.write(f"epoch {epoch+1} test acc:{test_acc} train acc:{train_acc}"+"\n")

        if (epoch+1)*100.0/num_epochs >= cnt:
            print("\033[F",end='')
            clear_line()
            print("\033[F",end='')
            clear_line()
            print(cnt,"% epochs done")
            print("done 0 % of an epoch")
            cnt+=10
            
        if scheduler:
            if scheduler.__module__ == lr_scheduler.__name__:
                # UsingPyTorchIn-Builtscheduler
                scheduler.step()
            else:
                # Usingcustomdefinedscheduler
                for param_group in opt.param_groups:
                    param_group['lr'] = scheduler(epoch)
                writer.add_scalar("lr",scheduler(epoch),epoch)

            
    print(f'loss {train_l:.3f}, train acc {train_acc:.3f}, '
          f'test acc {test_acc:.3f}')
    print(f'{metric[2] * num_epochs / timer.sum():.1f} examples/sec '
          f'on {str(device)}')
    return train_l,train_acc,test_acc,opt

def start_train(batch_size=1024):
    train_iter = get_dataloader('data',batch_size,'train',shuffle=True,num_workers=4)
    test_iter = get_dataloader('data',batch_size,'test',shuffle=True,num_workers=4)
    net = getnet()
    lr = 0.1
    wd = 1e-5
    epoch = 100
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    start = datetime.now()
    
    writer = SummaryWriter('log',f'{start.strftime("%m月%d日%H;%M;%S")}_{lr}_{wd}')
    optimizer = torch.optim.Adam(params=net.parameters(),lr=lr,weight_decay=wd)
    train_l,train_acc,test_acc,opt = train(net,train_iter,test_iter,epoch,device,writer,optimizer)
    save_paramter(net,optimizer)
    writer.close()
    print("train_l,train_acc,test_acc",train_l,train_acc,test_acc)
    

if __name__=='__main__':
    start_train(4096)