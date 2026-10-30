"""One offline, memory-only WAV scoring request per process."""
import contextlib
import json
import sys
from training.pretrained_audio import ASTDogAudio,MAX_BYTES,read_wav_bytes

def main():
    raw=sys.stdin.buffer.read(MAX_BYTES+1)
    with contextlib.redirect_stdout(sys.stderr):
        signal,digest=read_wav_bytes(raw)
        result=ASTDogAudio().analyze(signal,digest)
    encoded=json.dumps(result,allow_nan=False).encode()
    if len(encoded)>64000:raise ValueError('Oversized result')
    sys.stdout.buffer.write(encoded);sys.stdout.buffer.flush()

if __name__=='__main__':main()
