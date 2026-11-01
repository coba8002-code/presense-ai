"""Bounded official-feed metadata automation; analysis/training are separate opt-ins."""
import argparse
from contextlib import closing
import fcntl
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import httpx
from pydantic import BaseModel,ConfigDict,Field,field_validator
from knowledge.pipeline import open_db
from knowledge.providers import CHANNEL_ID,canonical

class AutomationConfig(BaseModel):
 model_config=ConfigDict(extra='forbid',strict=True)
 channels:list[str]=Field(default_factory=list,max_length=20)
 interval_seconds:int=Field(default=3600,ge=300,le=86400)
 daily_feed_requests:int=Field(default=20,ge=1,le=1000)
 retention_days:int=Field(default=7,ge=1,le=30)
 knowledge_config:str|None=None
 enable_link_analysis:bool=False
 paid_link_analysis_approved:bool=False
 audio_inbox:str|None=None
 training_output:str|None=None
 enable_local_training:bool=False
 @field_validator('channels')
 @classmethod
 def channels_valid(cls,value):
  if len(set(value))!=len(value) or any(not CHANNEL_ID.fullmatch(v) for v in value):raise ValueError('Distinct canonical YouTube channel IDs required')
  return value
 @field_validator('knowledge_config','audio_inbox','training_output')
 @classmethod
 def local_paths(cls,value):
  if value is not None and (not value.strip() or '://' in value):raise ValueError('Explicit local paths only')
  return value

def schema(db):
 db.executescript('''CREATE TABLE IF NOT EXISTS research_links(id TEXT PRIMARY KEY,title TEXT NOT NULL,channel_id TEXT,verification TEXT NOT NULL,evidence_url TEXT NOT NULL,discovery_query TEXT NOT NULL,first_seen REAL NOT NULL,last_seen REAL NOT NULL,expires REAL NOT NULL);
 CREATE TABLE IF NOT EXISTS feed_usage(day INTEGER PRIMARY KEY,count INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS feed_cache(channel_id TEXT PRIMARY KEY,etag TEXT NOT NULL,modified TEXT NOT NULL);
 CREATE TABLE IF NOT EXISTS automation_status(id INTEGER PRIMARY KEY CHECK(id=1),started REAL NOT NULL,payload TEXT NOT NULL);''')

def import_candidates(db,items,now=None,retention_days=7):
 now=time.time() if now is None else now
 if not isinstance(items,list) or len(items)>100 or type(retention_days) is not int or not 1<=retention_days<=30:raise ValueError('Bounded candidates required')
 parsed=[]
 for item in items:
  vid=item['video_id'];canonical(vid);title=item['title'];q=item['query'];e=item['evidence_url'];u=urlsplit(e)
  if not all(isinstance(v,str) and 1<=len(v)<=2048 for v in (title,q,e)) or len(title)>300 or len(q)>200 or u.scheme!='https' or not u.hostname or u.username or u.password:raise ValueError('Public indexed metadata required')
  parsed.append((vid,title,None,'search_index_only',e,q,now,now,now+retention_days*86400))
 schema(db)
 with db:
  for row in parsed:
   # Search indexing must never downgrade verified official feed metadata.
   db.execute('INSERT INTO research_links VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,expires=excluded.expires',row)
 return len(parsed)

def _feed(db,cfg,client,channel,now):
 day=int(now//86400)
 with db:
  db.execute('INSERT OR IGNORE INTO feed_usage VALUES(?,0)',(day,))
  if db.execute('SELECT count FROM feed_usage WHERE day=?',(day,)).fetchone()[0]>=cfg.daily_feed_requests:raise ValueError('Feed request budget')
  db.execute('UPDATE feed_usage SET count=count+1 WHERE day=?',(day,));db.execute('DELETE FROM feed_usage WHERE day<?',(day-30,))
 cache=db.execute('SELECT etag,modified FROM feed_cache WHERE channel_id=?',(channel,)).fetchone();headers={}
 if not db.execute('SELECT 1 FROM research_links WHERE channel_id=? AND expires>? LIMIT 1',(channel,now)).fetchone():cache=None
 if cache:
  if cache[0]:headers['If-None-Match']=cache[0]
  if cache[1]:headers['If-Modified-Since']=cache[1]
 raw=bytearray()
 with client.stream('GET','https://www.youtube.com/feeds/videos.xml',params={'channel_id':channel},headers=headers,timeout=10,follow_redirects=False) as r:
  if r.status_code==304:
   if not cache:raise ValueError('Unexpected unconditionally cached feed')
   with db:db.execute('UPDATE research_links SET last_seen=?,expires=? WHERE channel_id=? AND verification=?',(now,now+cfg.retention_days*86400,channel,'official_feed_metadata_only'))
   return 0
  if r.status_code!=200 or r.headers.get('content-type','').split(';')[0] not in ('application/atom+xml','application/xml','text/xml'):raise ValueError('Official feed unavailable')
  for chunk in r.iter_bytes():
   raw.extend(chunk)
   if len(raw)>256000:raise ValueError('Feed too large')
  def safe_header(name):
   v=r.headers.get(name,'');return v if len(v)<=256 and all(32<=ord(c)<127 for c in v) else ''
  etag,modified=safe_header('etag'),safe_header('last-modified')
 if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('Unsupported XML declaration')
 root=ET.fromstring(raw);ns={'a':'http://www.w3.org/2005/Atom','y':'http://www.youtube.com/xml/schemas/2015'}
 if root.tag!='{http://www.w3.org/2005/Atom}feed' or root.findtext('y:channelId',namespaces=ns)!=channel:raise ValueError('Feed/channel mismatch')
 entries=root.findall('a:entry',ns)
 if len(entries)>100:raise ValueError('Feed entry limit')
 parsed=[]
 for e in entries:
  vid=e.findtext('y:videoId',namespaces=ns);canonical(vid)
  if e.findtext('y:channelId',namespaces=ns)!=channel:raise ValueError('Entry channel mismatch')
  title=e.findtext('a:title',default='',namespaces=ns).strip()[:300]
  if not title:raise ValueError('Missing title')
  parsed.append((vid,title,channel,'official_feed_metadata_only',canonical(vid),'official_channel_feed',now,now,now+cfg.retention_days*86400))
 with db:
  for row in parsed:db.execute('INSERT INTO research_links VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,channel_id=excluded.channel_id,verification=excluded.verification,last_seen=excluded.last_seen,expires=excluded.expires',row)
  db.execute('INSERT OR REPLACE INTO feed_cache VALUES(?,?,?)',(channel,etag,modified))
 return len(parsed)

def cycle(db,config,client,env,now=None,force=False):
 cfg=AutomationConfig.model_validate(config);now=time.time() if now is None else now;schema(db)
 path=db.execute('PRAGMA database_list').fetchone()['file']
 with open(path+'.source-worker.lock','a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('Source worker already running') from None
  previous=db.execute('SELECT started FROM automation_status WHERE id=1').fetchone()
  if previous and not force and now-previous[0]<cfg.interval_seconds:return {'status':'waiting_interval','next_due':previous[0]+cfg.interval_seconds}
  report={'status':'completed','discovered':0,'feed_errors':0,'video_media_downloads':0,'link_analysis':{'status':'disabled'},'local_training':{'status':'disabled'},'notice':'Metadata discovery does not verify video content, rights, expert claims or training readiness.'}
  with db:
   db.execute('DELETE FROM research_links WHERE expires<=?',(now,))
   db.execute('INSERT OR REPLACE INTO automation_status VALUES(1,?,?)',(now,json.dumps({'status':'running','started':now})))
  for channel in cfg.channels:
   try:report['discovered']+=_feed(db,cfg,client,channel,now)
   except (httpx.HTTPError,ValueError,ET.ParseError,TypeError,KeyError):report['feed_errors']+=1
  if cfg.enable_link_analysis:
   if not cfg.paid_link_analysis_approved:report['link_analysis']={'status':'blocked','reason':'external_analysis_budget_approval_missing'}
   elif not cfg.knowledge_config or env.get('PETSENSE_ENABLE_KNOWLEDGE','').lower()!='true' or not all(env.get(k) for k in ('YOUTUBE_API_KEY','GEMINI_API_KEY')):report['link_analysis']={'status':'blocked','reason':'configuration_or_credentials_missing'}
   else:
    try:
     from knowledge.worker import load_config
     from knowledge.providers import Providers
     from knowledge.pipeline import cycle as knowledge_cycle
     k=load_config(cfg.knowledge_config)
     if k.notebook and not (env.get('GOOGLE_ACCESS_TOKEN') or env.get('GOOGLE_ACCESS_TOKEN_FILE')):raise ValueError('Notebook credentials missing')
     summary=knowledge_cycle(db,k,Providers(k,client,env),now=now)
     report['link_analysis']={'status':'cycle_executed','summary':summary}
    except (ValueError,OSError,sqlite3.Error):report['link_analysis']={'status':'blocked','reason':'rights_provider_or_configuration_unavailable'}
  if cfg.enable_local_training:
   if not cfg.audio_inbox or not cfg.training_output:report['local_training']={'status':'blocked','reason':'local_reviewed_job_paths_missing'}
   else:
    try:
     from training.autolearn import scan
     results=scan(cfg.audio_inbox,cfg.training_output)
     # Do not expose provider/path/validation exception strings in status/UI.
     report['local_training']={'status':'scanned','jobs':[{'status':r['status'],'decision':r.get('decision')} for r in results]}
    except (ValueError,OSError):report['local_training']={'status':'blocked','reason':'rights_review_or_local_job_validation_failed'}
  if report['feed_errors']:report['status']='completed_with_blocks'
  with db:db.execute('UPDATE automation_status SET payload=? WHERE id=1',(json.dumps(report,allow_nan=False),))
  return report

def status(db,now=None):
 now=time.time() if now is None else now
 names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
 if not {'research_links','automation_status'}<=names:return {'status':'not_initialized','links':[],'training_ready':False}
 row=db.execute('SELECT started,payload FROM automation_status WHERE id=1').fetchone()
 last=None
 if row:
  raw=json.loads(row[1])
  # Only allow public operational fields; never expose local job names, paths,
  # provider exceptions or nested configuration from the worker's private DB.
  last={k:raw[k] for k in ('status','discovered','feed_errors','video_media_downloads') if k in raw}
  for k in ('link_analysis','local_training'):
   value=raw.get(k,{})
   last[k]={'status':value.get('status','not_run')}
   if k=='link_analysis':
    last[k]['counts']={name:value.get('summary',{}).get(name,0) for name in ('discovered','analyzed','synced','blocked','errors')}
 links=[{'video_id':r[0],'title':r[1],'channel_id':r[2],'verification':r[3],'url':canonical(r[0]),'training_ready':False,'analysis_status':'not_analyzed'} for r in db.execute('SELECT id,title,channel_id,verification FROM research_links WHERE expires>? ORDER BY last_seen DESC,id LIMIT 100',(now,))]
 return {'status':'worker_status_available' if row else 'candidates_only','last_cycle_at':row[0] if row else None,'last_cycle':last,'links':links,'training_ready':False,'notice':'Candidate metadata only; no source is automatically approved or trained.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--db',type=Path,required=True);p.add_argument('--seed',type=Path);p.add_argument('--watch',action='store_true');p.add_argument('--status',action='store_true');a=p.parse_args()
 try:
  if a.config.stat().st_size>64000:raise ValueError('Config too large')
  cfg=AutomationConfig.model_validate_json(a.config.read_bytes())
  with closing(open_db(a.db)) as db:
   if a.seed:
    if a.seed.stat().st_size>128000:raise ValueError('Seed too large')
    import_candidates(db,json.loads(a.seed.read_bytes()),retention_days=cfg.retention_days)
   if a.status:print(json.dumps(status(db),ensure_ascii=False));return
   with httpx.Client() as client:
    while True:
     if a.config.stat().st_size>64000:raise ValueError('Config too large')
     cfg=AutomationConfig.model_validate_json(a.config.read_bytes())
     print(json.dumps(cycle(db,cfg,client,os.environ),ensure_ascii=False,allow_nan=False),flush=True)
     if not a.watch:break
     time.sleep(min(cfg.interval_seconds,60))
 except KeyboardInterrupt:pass
 except (OSError,ValueError,sqlite3.Error):p.exit(2,'Source automation blocked: check local config, permissions and provider availability.\n')
if __name__=='__main__':main()
