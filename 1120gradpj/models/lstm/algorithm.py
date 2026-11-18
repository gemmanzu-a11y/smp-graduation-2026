"""Past-only encoder plus 72 target contexts. Direct output, no teacher forcing."""
import copy
import numpy as np
import torch
from torch import nn


class Network(nn.Module):
    def __init__(self,n_history,n_context,hidden_size=32,layers=1,dropout=0.0):
        super().__init__()
        self.encoder=nn.LSTM(n_history,hidden_size,num_layers=layers,batch_first=True,
                             dropout=dropout if layers>1 else 0.0)
        self.head=nn.Sequential(nn.Linear(hidden_size+n_context,hidden_size),nn.ReLU(),nn.Linear(hidden_size,1))
    def forward(self,history,context):
        _,(hidden,_)=self.encoder(history)
        state=hidden[-1].unsqueeze(1).expand(-1,72,-1)
        return self.head(torch.cat((state,context),dim=-1)).squeeze(-1)


class Estimator:
    def __init__(self,params,seed=42,jobs=2):
        self.params=dict(params);self.seed=seed;torch.set_num_threads(jobs)
    @staticmethod
    def check(history,context,y=None):
        if history.ndim!=3 or context.ndim!=3 or context.shape[1]!=72 or len(history)!=len(context) or not len(history):
            raise ValueError('Expected history [N,L,H] and context [N,72,F]')
        if y is not None and y.shape!=(len(history),72):raise ValueError('Expected labels [N,72]')
        if any(not np.isfinite(x).all() for x in [history,context]+([] if y is None else [y])):
            raise ValueError('Nonfinite model input')
    def transform(self,history,context):
        self.check(history,context)
        return (torch.tensor((history-self.history_mean)/self.history_scale,dtype=torch.float32),
                torch.tensor((context-self.context_mean)/self.context_scale,dtype=torch.float32))
    def fit(self,history,context,y,validation):
        self.check(history,context,y);vh,vc,vy=validation;self.check(vh,vc,vy)
        torch.manual_seed(self.seed);np.random.seed(self.seed);torch.use_deterministic_algorithms(True)
        self.history_mean=history.mean(axis=(0,1));self.history_scale=np.maximum(history.std(axis=(0,1)),1e-6)
        self.context_mean=context.mean(axis=(0,1));self.context_scale=np.maximum(context.std(axis=(0,1)),1e-6)
        self.y_mean=float(y.mean());self.y_scale=max(float(y.std()),1e-6)
        self.dimensions=(history.shape[2],context.shape[2]);self.lookback=history.shape[1]
        self.net=Network(*self.dimensions,self.params['hidden_size'],self.params['layers'],self.params.get('dropout',0))
        optimizer=torch.optim.Adam(self.net.parameters(),lr=self.params['learning_rate'],weight_decay=self.params.get('weight_decay',0))
        h,c=self.transform(history,context);targets=torch.tensor((y-self.y_mean)/self.y_scale,dtype=torch.float32)
        best=float('inf');state=None;wait=0;self.history=[]
        generator=torch.Generator().manual_seed(self.seed)
        for epoch in range(1,self.params['epochs']+1):
            self.net.train();total=0
            for idx in torch.randperm(len(h),generator=generator).split(self.params['batch_size']):
                optimizer.zero_grad();loss=nn.functional.mse_loss(self.net(h[idx],c[idx]),targets[idx])
                if not torch.isfinite(loss):raise ValueError('Nonfinite training loss')
                loss.backward();nn.utils.clip_grad_norm_(self.net.parameters(),1.0);optimizer.step()
                total+=float(loss.detach())*len(idx)
            score=float(np.abs(self.predict(vh,vc)-vy).mean())
            self.history.append(dict(epoch=epoch,train_scaled_mse=total/len(h),validation_mae=score))
            if score<best-self.params.get('min_delta',1e-4):
                best=score;state=copy.deepcopy(self.net.state_dict());self.best_epoch=epoch;wait=0
            else:wait+=1
            if wait>=self.params['patience']:break
        self.net.load_state_dict(state);self.validation_mae=best
        return self
    def predict(self,history,context):
        h,c=self.transform(history,context);self.net.eval();parts=[]
        with torch.no_grad():
            for i in range(0,len(h),128):parts.append(self.net(h[i:i+128],c[i:i+128]).numpy())
        return np.concatenate(parts)*self.y_scale+self.y_mean
    def save(self,path):
        state={key:getattr(self,key) for key in ['params','seed','dimensions','lookback','y_mean','y_scale','best_epoch','validation_mae','history']}
        for key in ['history_mean','history_scale','context_mean','context_scale']:state[key]=getattr(self,key).tolist()
        state['state_dict']=self.net.state_dict();torch.save(state,path)
    @classmethod
    def load(cls,path,jobs=2):
        state=torch.load(path,map_location='cpu',weights_only=True)
        model=cls(state['params'],seed=state['seed'],jobs=jobs)
        for key,value in state.items():
            if key!='state_dict':setattr(model,key,np.asarray(value,dtype='float32') if key.endswith(('_mean','_scale')) and isinstance(value,list) else value)
        model.net=Network(*model.dimensions,model.params['hidden_size'],model.params['layers'],model.params.get('dropout',0))
        model.net.load_state_dict(state['state_dict']);return model
