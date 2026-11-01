"""Summarize caller-supplied frame observations; never calls a model or opens media."""
import argparse
import json
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from backend.behavior_evidence import Frame, summarize

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    same_dog_confirmed:bool
    frames:list[Frame]=Field(min_length=1,max_length=30)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.input.stat().st_size>100000:raise ValueError('Input too large')
    data=Input.model_validate_json(args.input.read_bytes())
    result=summarize(data.frames,same_dog_confirmed=data.same_dog_confirmed)
    # Exclusive output: no overwriting existing observations or evaluation evidence.
    with args.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False)

if __name__=='__main__':main()
