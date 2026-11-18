"""Generation-supplement v4: reuse the identical common preprocessing contract."""
from pathlib import Path
import json,hashlib
from . import common_v3 as base
ROOT=base.ROOT;WORK=base.WORK;SHA=base.SHA;TZ=base.TZ;SOURCE=base.SOURCE
HISTORY=base.HISTORY;GROUPS=base.GROUPS;dump=base.dump;times=base.times;arrays=base.arrays
GENERATION=WORK/'shared_datasets/kpx_generation/20261119_v2/generation_2023_2025_hourly.csv'
GENERATION_HASH=json.loads((GENERATION.parent/'manifest.json').read_text())['files'][GENERATION.name]['sha256']
VERSION='v4_'+SHA[:12]+'_generation_'+GENERATION_HASH[:8]+'_lag72'
OUT=WORK/'SMP_SHARED_DATA/versions'/VERSION

def load(path=OUT):return base.load(path)

def build():
    if hashlib.sha256(GENERATION.read_bytes()).hexdigest()!=GENERATION_HASH:raise ValueError('Generation SHA256 mismatch')
    result=base.build(generation_path=GENERATION,output_dir=OUT,dataset_version=VERSION)
    # Preserve exactly the original comparison dates and feature definitions.
    old_h,old_f,old_m=base.load();h,f,m=load()
    import pandas as pd
    pd.testing.assert_index_equal(h.index,old_h.index)
    for name in ['evaluation_origins.csv','evaluation_targets.csv']:
        if (OUT/name).read_bytes()!=(base.OUT/name).read_bytes():raise ValueError('Evaluation rows changed')
    changed=[c for c in h if not h[c].equals(old_h[c])]
    allowed=[c for c in h if c.startswith(('generation_lng','generation_coal','generation_nuclear'))]
    if set(changed)-set(allowed):raise ValueError('Non-generation history changed')
    assert m['context_features']==old_m['context_features'] and m['history_features']==old_m['history_features']
    stable=[c for c in f if not c.startswith(('generation_lng','generation_coal','generation_nuclear'))]
    pd.testing.assert_frame_equal(f[stable],old_f[stable])
    m['changed_history_columns']=changed;m['original_dataset_version']=base.VERSION
    dump(OUT/'manifest.json',m)
    print('PASS generation-only changes; identical origins/targets and all other input groups',flush=True)
    return result

if __name__=='__main__':build()
