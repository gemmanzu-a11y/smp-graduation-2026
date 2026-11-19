"""Train-only scalers, direct 72h prediction, optional known-weekly residual target."""
import copy
import numpy as np
import torch
from torch import nn

class Network(nn.Module):
    def __init__(self,nh,nc,hidden):
        super().__init__();self.encoder=nn.LSTM(nh,hidden,batch_first=True)
        self.head=nn.Sequential(nn.Linear(hidden+nc,hidden),nn.ReLU(),nn.Linear(hidden,1))
    def forward(self,h,x):
        _,(state,_)=self.encoder(h)
        return self.head(torch.cat([state[-1][:,None,:].expand(-1,72,-1),x],dim=-1)).squeeze(-1)

class Estimator:
    def __init__(self,params):self.params=dict(params);torch.set_num_threads(2)
    def fit(self,h,x,y,baseline,validation=None,epochs=None):
        torch.manual_seed(42);np.random.seed(42);torch.use_deterministic_algorithms(True)
        if not all(np.isfinite(a).all() for a in [h,x,y,baseline]):raise ValueError('Nonfinite input')
        self.lookback=h.shape[1];self.dimensions=(h.shape[2],x.shape[2])
        self.hm=h.mean((0,1));self.hs=h.std((0,1));self.hs=np.where(self.hs<1e-6,1.,self.hs)
        self.xm=x.mean((0,1));self.xs=x.std((0,1));self.xs=np.where(self.xs<1e-6,1.,self.xs)
        target=y-baseline if self.params['target']=='weekly_residual' else y
        self.ym=float(target.mean());self.ys=max(float(target.std()),1e-6)
        self.net=Network(*self.dimensions,self.params['hidden']);optimizer=torch.optim.Adam(self.net.parameters(),lr=self.params['lr'],weight_decay=.001)
        hh,xx=self.transform(h,x);yy=torch.tensor((target-self.ym)/self.ys,dtype=torch.float32)
        generator=torch.Generator().manual_seed(42);best=float('inf');state=None;wait=0;self.history=[]
        limit=epochs if epochs is not None else self.params['max_epochs']
        for epoch in range(1,limit+1):
            self.net.train();total=0.
            for ids in torch.randperm(len(hh),generator=generator).split(32):
                optimizer.zero_grad();p=self.net(hh[ids],xx[ids]);t=yy[ids]
                if self.params['loss']=='mse':loss=nn.functional.mse_loss(p,t)
                elif self.params['loss']=='mae':loss=nn.functional.l1_loss(p,t)
                else:loss=nn.functional.smooth_l1_loss(p,t,beta=1.)
                if not torch.isfinite(loss):raise RuntimeError('Nonfinite loss')
                loss.backward();nn.utils.clip_grad_norm_(self.net.parameters(),1.);optimizer.step();total+=float(loss.detach())*len(ids)
            record=dict(epoch=epoch,train_loss=total/len(h))
            if validation is not None:
                vh,vx,vy,vb=validation;score=float(np.abs(self.predict(vh,vx,vb)-vy).mean());record['tuning_mae']=score
                if score<best-1e-4:best=score;state=copy.deepcopy(self.net.state_dict());self.best_epoch=epoch;wait=0
                else:wait+=1
                if epoch==1 or epoch%5==0:print(self.params['id'],'epoch',epoch,'tuning_mae',round(score,4),flush=True)
            self.history.append(record)
            if validation is not None and wait>=self.params['patience']:break
        if validation is not None:self.net.load_state_dict(state)
        else:self.best_epoch=limit
        return self
    def transform(self,h,x):return (torch.tensor((h-self.hm)/self.hs,dtype=torch.float32),torch.tensor((x-self.xm)/self.xs,dtype=torch.float32))
    def predict(self,h,x,baseline):
        hh,xx=self.transform(h,x);self.net.eval();parts=[]
        with torch.no_grad():
            for i in range(0,len(hh),128):parts.append(self.net(hh[i:i+128],xx[i:i+128]).numpy())
        value=np.concatenate(parts).astype('float64')*self.ys+self.ym
        if self.params['target']=='weekly_residual':value=value+baseline
        if not np.isfinite(value).all():raise RuntimeError('Nonfinite prediction')
        return value
    def save(self,path):
        state=dict(params=self.params,lookback=self.lookback,dimensions=self.dimensions,ym=self.ym,ys=self.ys,best_epoch=self.best_epoch,history=self.history,state_dict=self.net.state_dict())
        for key in ['hm','hs','xm','xs']:state[key]=getattr(self,key).tolist()
        torch.save(state,path)
    @classmethod
    def load(cls,path):
        data=torch.load(path,map_location='cpu',weights_only=True);model=cls(data['params'])
        for k,v in data.items():
            if k!='state_dict':setattr(model,k,np.array(v,dtype='float32') if k in ['hm','hs','xm','xs'] else v)
        model.net=Network(*model.dimensions,model.params['hidden']);model.net.load_state_dict(data['state_dict']);return model
