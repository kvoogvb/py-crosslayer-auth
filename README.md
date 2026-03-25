## physical layer
> a submode
### api
#### val(claim_id: int|list,wifi_data_id:int|list): in val.py
> claim_id 用户声称的id  wifi_data_id 我们模拟的用户实际信号
    - xxx_id 取值[1,6] int ,必须同时为int或list,且长度相等
    - 返回: ans,cost  
        - ans:一个存储bool的list,表示认证成功与否,True为认证成功
        - cost:float,表示认证消耗的时间,单位是秒