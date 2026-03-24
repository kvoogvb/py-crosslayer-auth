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
from train import cal_test
import sys
import pandas as pd
import numpy as np

class Wifi_test_data:
    def __init__(self):
        self.dfs = []
        for i in range(1,7):
            df = pd.read_csv(f'data/{i}_test.csv')
            self.dfs.append(df)
    def get_random_row(self,usr_id,n=1):
        return self.dfs[usr_id-1].sample(n=n).iloc[0].values

data = Wifi_test_data()
model_name = 'save/v5_ok.pth'
model_cache = None


def load_model():
    net = getnet()
    checkpoint = torch.load(model_name)
    model_dict = net.state_dict()
    pretrained_dict = {k: v for k, v in checkpoint['model_state_dict'].items() 
            if k in model_dict and v.shape == model_dict[k].shape}
    model_dict.update(pretrained_dict)
    net.load_state_dict(model_dict,strict=True)
    model_cache = net
    return model_cache

#just for test
def test_model(model_path):
    net = getnet()
    net = load_model(net,model_path)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    net.to(device)
    test_iter = get_dataloader('data',4096,'test',single=False)
    acc,loss = cal_test(net,test_iter,torch.nn.CrossEntropyLoss(),device)
    print(acc)

def id2wifi(usr_id: int | list)->torch.tensor:
    if isinstance(usr_id,int):
        usr_id = [usr_id]
  
    if isinstance(usr_id,list):
        X = []
        for id in usr_id:
            X.append(data.get_random_row(id,n=1))
        X = np.array(X)
        X = torch.tensor(X,dtype=torch.float32)
        if len(X.shape) == 2:  # (batch, 256)
            X = X.unsqueeze(1) # -> (batch, 1, 256)
        return X
    return None

def val_test(usr_id: int | list):
    start = datetime.now()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    net = getnet()
    net = load_model(net,model_name)
    device = 'cpu'
    net.to(device)
    net.eval()

    start = datetime.now()
    if isinstance(usr_id,int):
        usr_id = [usr_id]
  
    if isinstance(usr_id,list):
        X = id2wifi(usr_id)
        X = X.to(device)
        
        with torch.no_grad():
            y_hat = net(X)
        pred_ids = torch.argmax(y_hat,dim=1) + 1
        pred_ids = pred_ids.cpu().tolist()
        ans = [pred == gt for pred,gt in zip(pred_ids,usr_id)]
        end = datetime.now()
        cost = (end-start).total_seconds()
        return ans,cost
    
def val_user(usr_id: int|list,wifi_data:torch.tensor):
    if  model_cache is None:
        net = load_model()
    else:
        net = model_cache
    device = 'cpu'
    net.to(device)
    net.eval()

    start = datetime.now()
    if isinstance(usr_id,int):
        usr_id = [usr_id]
  
    if isinstance(usr_id,list):
        X = wifi_data
        X = X.to(device)
        
        with torch.no_grad():
            y_hat = net(X)
        pred_ids = torch.argmax(y_hat,dim=1) + 1
        pred_ids = pred_ids.cpu().tolist()
        ans = [pred == gt for pred,gt in zip(pred_ids,usr_id)]
        end = datetime.now()
        cost = (end-start).total_seconds()
        return ans,cost

def val(claim_id: int|list,wifi_data_id:int|list):
    if not (isinstance(claim_id,int) and isinstance(wifi_data_id,int)):
        if not (isinstance(claim_id,list) and isinstance(wifi_data_id,list)):
            print("claim_id not match wifi_data_id")
            return None,None
        else:
            assert len(claim_id) == len(wifi_data_id),"claim_id length not match wifi_data_id"

    wifi_data = id2wifi(wifi_data_id)
    return val_user(claim_id,wifi_data)

ans,cost = val([1,2,3,4,5,6],[1,2,3,3,3,3])
print(ans,cost)



    
