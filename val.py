import torch
from datetime import datetime
from dataloader import get_dataloader
from model import getnet
from train import cal_test
import sys
import pandas as pd
import numpy as np

class Wifi_test_data:
    def __init__(self,data_dir:str = 'data'):
        self.dfs = []
        for i in range(1,7):
            df = pd.read_csv(f'{data_dir}/{i}_test.csv')
            self.dfs.append(df)
    def get_random_row(self,usr_id,n=1):
        return self.dfs[usr_id-1].sample(n=n).iloc[0].values

data = Wifi_test_data()


def load_model(net,path):
    checkpoint = torch.load(path)
    model_dict = net.state_dict()
    pretrained_dict = {k: v for k, v in checkpoint['model_state_dict'].items() 
            if k in model_dict and v.shape == model_dict[k].shape}
    model_dict.update(pretrained_dict)
    net.load_state_dict(model_dict,strict=True)
    return net

def test_model(model_path):
    net = getnet()
    net = load_model(net,model_path)
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    net.to(device)
    test_iter = get_dataloader('data',4096,'test',single=False)
    acc,loss = cal_test(net,test_iter,torch.nn.CrossEntropyLoss(),device)
    print(acc)

def val(usr_id: int | list,data_dir:str = 'data'):
    start = datetime.now()
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    net = getnet()
    net = load_model(net,'v5_ok.pth')
    device = 'cpu'
    net.to(device)
    net.eval()

    start = datetime.now()
    if isinstance(usr_id,int):
        usr_id = [usr_id]
  
    if isinstance(usr_id,list):
        X = []
        for id in usr_id:
            X.append(data.get_random_row(id,n=1))
        X = np.array(X)
        X = torch.tensor(X,dtype=torch.float32)
        if len(X.shape) == 2:  # (batch, 256)
            X = X.unsqueeze(1)  # -> (batch, 1, 256)
        X = X.to(device)
        
        with torch.no_grad():
            y_hat = net(X)
        pred_ids = torch.argmax(y_hat,dim=1) + 1
        pred_ids = pred_ids.cpu().tolist()
        ans = [pred == gt for pred,gt in zip(pred_ids,usr_id)]
        end = datetime.now()
        cost = (end-start).total_seconds()
        return ans,cost
    
def val_test(ids=None):
    
    if ids is None:
        n = len(sys.argv) - 1
        if n == 0:
            print("usage python val.py id1 id2 ...")
        ids = sys.argv[1:]
    n = len(ids)
    for id in ids:
        assert id in [1,2,3,4,5,6],"wrong id"
    pred,gt = val(ids)
    sum_right = 0
    for i in range(n):
        if pred[i] == gt[i]: sum_right+=1
    print(f'acc:{sum_right/n*100} %')

ans,cost = val(1)
# ans,cost = val([1,1,1,1,1,1])
print(ans,cost)
# test_model('v2_ok.pth')

    

    
