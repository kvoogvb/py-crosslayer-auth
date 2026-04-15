## physical layer
> a submode
### env
- python > 3.10
- (依赖请参考项目根目录的 requirements.txt)
### api
#### Val(self,data_dir:str = 'data',model_name = 'save/v5_ok.pth')
- data_dir: 数据目录
- model_name: 模型文件
#### Val.val(claim_id: int|list,wifi_data_id:int|list): in val.py
> claim_id 用户声称的id  wifi_data_id 我们模拟的用户的实际wifi信号,这里的输入是id (纯软,wifi信号有限)
- xxx_id 取值[1,6] int ,必须同时为int或list,且长度相等
- 返回: ans,cost  
    - ans:一个存储bool的list,表示认证成功与否,True为认证成功
    - cost:float,表示认证消耗的时间,单位是秒