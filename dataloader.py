import os
import torch
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np


class CSVDataset(Dataset):
    """从 i_train.csv / i_test.csv 文件中加载数据的Dataset"""
    
    def __init__(self, data_dir: str, mode: str = 'train'):
        """
        Args:
            data_dir: CSV文件所在目录
            mode: 'train' 或 'test'
        """
        self.samples = []
        
        for i in range(1, 7):  # i = 1,2,3,4,5,6 对应 6个类别
            filename = f"{i}_{mode}.csv"
            filepath = os.path.join(data_dir, filename)
            
            if not os.path.exists(filepath):
                print(f"Warning: {filepath} not found, skipping...")
                continue
            
            # 读取CSV（假设每行是特征向量，最后一列可能是标签，否则全部作为特征）
            df = pd.read_csv(filepath, header=None)
            
            # 转换为numpy数组
            data = df.values.astype(np.float32)
            
            # 每行数据 + 标签(i-1，转换为0-indexed)
            for row in data:
                self.samples.append((row, i - 1))
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        features, label = self.samples[idx]
        return (
            torch.tensor(features, dtype=torch.float32).unsqueeze(0),
            torch.tensor(label, dtype=torch.long)
        )


def get_dataloader(
    data_dir: str,
    batch_size: int = 32,
    mode: str = 'train',
    shuffle: bool = True,
    num_workers: int = 0
) -> DataLoader:
    """
    返回DataLoader
    
    Args:
        data_dir: CSV文件目录
        batch_size: 批次大小
        mode: 'train' 或 'test'
        shuffle: 是否打乱
        num_workers: 数据加载线程数
    
    Returns:
        DataLoader对象
    """
    dataset = CSVDataset(data_dir, mode)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=True  # 加速GPU传输
    )