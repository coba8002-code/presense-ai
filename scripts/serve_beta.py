"""Fail-closed API entrypoint behind a local trusted TLS reverse proxy."""
import os
from scripts.beta_preflight import inspect

def main():
    if not inspect(os.environ)['configuration_ready_for_private_beta']:
        raise SystemExit('Private beta configuration blocked. Run python -m scripts.beta_preflight; no secrets are printed.')
    import uvicorn
    uvicorn.run('backend.app:app',host='127.0.0.1',port=8000,workers=1,proxy_headers=True,forwarded_allow_ips='127.0.0.1',access_log=False)
if __name__=='__main__':main()
