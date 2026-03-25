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

data = None

model_cache = None
class Val:
    def __init__(self,data_dir:str = 'data',model_name = 'save/v5_ok.pth'):
        self.data = Wifi_test_data(data_dir=data_dir)
        self.model_cache = self.load_model(model_name)

    def load_model(self,model_name:str=None):
        if self.model_cache is not None and model_name is None:
            return self.model_cache
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
    def test_model(self,model_path):
        net = self.load_model(model_path)
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        net.to(device)
        test_iter = get_dataloader('data',4096,'test',single=False)
        acc,loss = cal_test(net,test_iter,torch.nn.CrossEntropyLoss(),device)
        print(acc)

    def id2wifi(self,usr_id: int | list)->torch.tensor:
        if isinstance(usr_id,int):
            usr_id = [usr_id]
    
        if isinstance(usr_id,list):
            X = []
            for id in usr_id:
                X.append(self.data.get_random_row(id,n=1))
            X = np.array(X)
            X = torch.tensor(X,dtype=torch.float32)
            if len(X.shape) == 2:  # (batch, 256)
                X = X.unsqueeze(1) # -> (batch, 1, 256)
            return X
        return None

    def val_test(self,usr_id: int | list):
        start = datetime.now()
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        net = self.load_model()
        device = 'cpu'
        net.to(device)
        net.eval()

        start = datetime.now()
        if isinstance(usr_id,int):
            usr_id = [usr_id]
    
        if isinstance(usr_id,list):
            X = self.id2wifi(usr_id)
            X = X.to(device)
            
            with torch.no_grad():
                y_hat = net(X)
            pred_ids = torch.argmax(y_hat,dim=1) + 1
            pred_ids = pred_ids.cpu().tolist()
            ans = [pred == gt for pred,gt in zip(pred_ids,usr_id)]
            end = datetime.now()
            cost = (end-start).total_seconds()
            return ans,cost
        
    def val_user(self,usr_id: int|list,wifi_data:torch.tensor):
        net = self.load_model()
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

    def val(self,claim_id: int|list,wifi_data_id:int|list):
        if not (isinstance(claim_id,int) and isinstance(wifi_data_id,int)):
            if not (isinstance(claim_id,list) and isinstance(wifi_data_id,list)):
                print("claim_id not match wifi_data_id")
                return None,None
            else:
                assert len(claim_id) == len(wifi_data_id),"claim_id length not match wifi_data_id"

        wifi_data = self.id2wifi(wifi_data_id)
        return self.val_user(claim_id,wifi_data)

ans,cost = Val('data','save/v5_ok.pth').val([1,2,3,4,5,6],[1,2,3,3,3,3])
print(ans,cost)



    
