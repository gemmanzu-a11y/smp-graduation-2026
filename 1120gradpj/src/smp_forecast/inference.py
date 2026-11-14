"""Do not ship a current multivariate forecast when an entire trained input source is absent."""
import numpy as np
from .dataset import VARIABLES

def input_gate(x,lookback=48):
 seq=np.asarray(x[0,:lookback*len(VARIABLES)]).reshape(lookback,len(VARIABLES));issues=[]
 for i,name in enumerate(VARIABLES):
  fraction=float(np.isnan(seq[:,i]).mean())
  # SI normally lacks night observations. Other variables need some source history.
  if fraction>=1.0:issues.append(dict(variable=name,reason='all_requested_history_missing',missing_fraction=fraction))
 return dict(status='blocked_missing_input' if issues else 'research_input_available',can_predict=not issues,issues=issues,scope='research gate only; historical publication vintages remain unverified')
