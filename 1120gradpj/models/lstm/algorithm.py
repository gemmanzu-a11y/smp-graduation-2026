"""One recurrent encoder, condition-aware 72-output head; identical raw X to tabular models."""
import copy
import numpy as np
import torch
from torch import nn
class Network(nn.Module):
 def __init__(self,n_variables,n_context,hidden_size=48,layers=1):
  super().__init__();self.encoder=nn.LSTM(n_variables,hidden_size,num_layers=layers,batch_first=True);self.head=nn.Sequential(nn.Linear(hidden_size+n_context,64),nn.ReLU(),nn.Linear(64,1))
 def forward(self,seq,context):
  _,(h,_)=self.encoder(seq);embedding=h[-1].unsqueeze(1).expand(-1,context.shape[1],-1);return self.head(torch.cat([embedding,context],dim=-1)).squeeze(-1)
class Estimator:
 def __init__(self,params,lookback=48,n_variables=8,seed=42,jobs=4):
  self.params=params;self.lookback=lookback;self.n_variables=n_variables;self.seed=seed;torch.set_num_threads(jobs)
 def unpack(self,x):
  n=len(x)//72
  if n*72!=len(x):raise ValueError('LSTM requires full origin x 72 target blocks')
  x=x.reshape(n,72,-1);size=self.lookback*self.n_variables
  return torch.from_numpy(np.ascontiguousarray(x[:,0,:size].reshape(n,self.lookback,self.n_variables),dtype='float32')),torch.from_numpy(np.ascontiguousarray(x[:,:,size:],dtype='float32'))
 def fit(self,x,y,x_val,y_val):
  torch.manual_seed(self.seed);np.random.seed(self.seed);seq,context=self.unpack(x);vseq,vcontext=self.unpack(x_val)
  self.y_mean=float(np.mean(y));self.y_scale=max(float(np.std(y)),1e-6);yt=torch.tensor((y.reshape(-1,72)-self.y_mean)/self.y_scale,dtype=torch.float32)
  p=self.params;self.net=Network(self.n_variables,context.shape[-1],p['hidden_size'],p['layers']);opt=torch.optim.Adam(self.net.parameters(),lr=p['learning_rate']);best=float('inf');best_state=None;wait=0;self.history=[]
  generator=torch.Generator().manual_seed(self.seed)
  for epoch in range(1,p['epochs']+1):
   self.net.train();permutation=torch.randperm(len(seq),generator=generator);losses=[]
   for idx in permutation.split(p['batch_size']):
    opt.zero_grad();pred=self.net(seq[idx],context[idx]);loss=nn.functional.mse_loss(pred,yt[idx]);loss.backward();nn.utils.clip_grad_norm_(self.net.parameters(),1.0);opt.step();losses.append(float(loss.detach()))
   self.net.eval()
   with torch.no_grad():vpred=self.net(vseq,vcontext).numpy().reshape(-1)*self.y_scale+self.y_mean
   score=float(np.mean(np.abs(vpred-y_val)));self.history.append(dict(epoch=epoch,train_scaled_mse=float(np.mean(losses)),validation_mae=score))
   if epoch==1 or epoch%5==0:print('LSTM epoch',epoch,'validation MAE',round(score,4),flush=True)
   if score<best-1e-4:best=score;self.best_epoch=epoch;best_state=copy.deepcopy(self.net.state_dict());wait=0
   else:wait+=1
   if wait>=p['patience']:break
  self.net.load_state_dict(best_state);return self
 def predict(self,x):
  seq,c=self.unpack(x);self.net.eval();out=[]
  with torch.no_grad():
   for i in range(0,len(seq),128):out.append(self.net(seq[i:i+128],c[i:i+128]).numpy())
  return np.concatenate(out).reshape(-1)*self.y_scale+self.y_mean
 def save(self,path):
  torch.save(dict(state_dict=self.net.state_dict(),params=self.params,lookback=self.lookback,n_variables=self.n_variables,n_context=self.net.head[0].in_features-self.params['hidden_size'],y_mean=self.y_mean,y_scale=self.y_scale,best_epoch=self.best_epoch),path)
 @classmethod
 def load(cls,path,jobs=4):
  b=torch.load(path,map_location='cpu',weights_only=True);m=cls(b['params'],b['lookback'],b['n_variables'],jobs=jobs);m.net=Network(m.n_variables,b['n_context'],b['params']['hidden_size'],b['params']['layers']);m.net.load_state_dict(b['state_dict']);m.y_mean=b['y_mean'];m.y_scale=b['y_scale'];m.best_epoch=b['best_epoch'];return m
