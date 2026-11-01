"""Dog2vec feature comparison contract, not an unsafe checkpoint loader/classifier."""
import importlib.util
import numpy as np
from pydantic import BaseModel,ConfigDict,Field,model_validator

MODEL_RECORD={'repo':'https://github.com/fispresent/dog2vec','doi':'10.5281/zenodo.15494042','weight_license_metadata':'cc-by-4.0','file':'dog2vec_130k_9.pt','bytes':1135553458,'publisher_checksum':'md5:ca1c5a73388858e57b7a0c4ce691d315','code_license_verified':False,'training_source_rights_verified':False}
class Provenance(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 synthetic:bool
 checkpoint_sha256:str=Field(pattern='^[a-f0-9]{64}$')
 code_permission_evidence:str|None=Field(default=None,min_length=1,max_length=1200)
 layer:int=Field(default=9,ge=9,le=9)
 @model_validator(mode='after')
 def code_rights(self):
  if not self.synthetic and (not self.code_permission_evidence or not self.code_permission_evidence.strip()):raise ValueError('Explicit code-use evidence required before real extraction')
  return self

def readiness():
 return {**MODEL_RECORD,'fairseq_installed':importlib.util.find_spec('fairseq') is not None,'automatic_checkpoint_loading':False,'production_ready':False,'remaining':['Pin reviewed code revision/license and compatible runtime','Audit legacy Fairseq .pt deserialization; no arbitrary pickle load','Acquire/hash weights and independently verify data-use rights','Fit and independently test a task head on the same locked dog references as AST']}

def extract(signal,extractor,provenance):
 card=Provenance.model_validate(provenance);signal=np.asarray(signal,dtype=np.float32)
 if signal.ndim!=1 or not 1600<=len(signal)<=160000 or not np.all(np.isfinite(signal)) or np.max(np.abs(signal))>1:raise ValueError('Bounded mono16kHz signal required')
 # Trusted injected feature call only. No fairseq import/download/pickle or GPU here.
 features=np.asarray(extractor(signal),dtype=np.float64)
 if features.ndim!=2 or not 1<=features.shape[0]<=1000 or features.shape[1]!=768 or not np.all(np.isfinite(features)):raise ValueError('Expected bounded HuBERT-base feature matrix')
 pooled=features.mean(axis=0);norm=float(np.linalg.norm(pooled))
 return {'model':'Dog2vec-HuBERT-base-layer9','checkpoint_sha256':card.checkpoint_sha256,'synthetic':card.synthetic,'feature_dimension':768,'frames':features.shape[0],'mean_embedding':pooled.tolist(),'unit_embedding':(pooled/norm if norm>0 else np.zeros(768)).tolist(),'task_prediction':None,'decision':'abstain','production_ready':False,'limitations':['Injected feature contract only, not verified Dog2vec execution','Features are not bark classes or calibrated probabilities','Feature time alignment and downstream task head unvalidated']}
