"""Explicit public-weight preparation before starting the offline analysis service."""
import argparse
import os
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache-dir',required=True);a=p.parse_args()
    root=Path(a.cache_dir).resolve();root.mkdir(parents=True,exist_ok=True)
    os.environ['HF_HOME']=str(root);os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
    from training.pretrained_audio import ASTDogAudio,MODEL,REVISION
    ASTDogAudio()
    print(f'Prepared {MODEL} at {REVISION}. Use the same HF_HOME when starting the server. No animal inference performed.')

if __name__=='__main__':main()
