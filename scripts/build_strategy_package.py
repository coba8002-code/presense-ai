from pathlib import Path
import html,re,json,zipfile,subprocess,hashlib,shutil
root=Path(__file__).resolve().parents[1];dest=root/'artifacts/strategy-v6-20261028';dest.mkdir(exist_ok=True)
css='''body{margin:0;background:#f1f4ed;color:#173940;font-family:system-ui,sans-serif;line-height:1.9}header{background:#103740;color:white;padding:60px max(calc((100% - 1000px)/2),24px)}header small{color:#cce694;letter-spacing:3px}header h1{font-size:36px;line-height:1.4}main{max-width:1060px;margin:30px auto;padding:0 24px}section{background:white;border-radius:18px;padding:32px;margin:22px 0;border:1px solid #dce6d8}h2{color:#087c80;font-size:24px}p{white-space:normal}table{border-collapse:collapse;width:100%;font-size:13px;line-height:1.7;margin:24px 0}th{background:#087c80;color:white}td,th{padding:12px;text-align:left;border-bottom:1px solid #dce6d8}tr:nth-child(even){background:#f2f6ec}a{color:#087c80;overflow-wrap:anywhere}.note{padding:16px;background:#e9f1d5;border-left:4px solid #087c80}nav a{display:inline-block;padding:10px 18px;background:white;border-radius:8px;margin:6px;text-decoration:none}footer{padding:24px;text-align:center;font-size:12px}@media(max-width:700px){section{padding:18px}table{display:block;overflow:auto}header h1{font-size:28px}}@media print{body{background:white;font-size:10pt}header{padding:20px;background:white;color:#103740}main{padding:0}section{border:0;padding:0;border-radius:0;break-inside:auto}h2{break-after:avoid}tr{break-inside:avoid}nav{display:none}}'''
def txt(s):
 return re.sub(r'(https?://[^\s<]+)',r'<a href="\1">\1</a>',html.escape(s))
links=[]
for file in sorted((root/'docs/strategy-20261028').glob('*.md')):
 shutil.copy2(file,dest/file.name)
 lines=file.read_text().splitlines();title=lines[0].lstrip('# ');parts=[];section=False;i=1
 while i<len(lines):
  line=lines[i]
  if line.startswith('## '):
   if section:parts.append('</section>')
   parts.append('<section><h2>'+txt(line[3:])+'</h2>');section=True
  elif line.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].startswith('|'):
    rows.append(lines[i]);i+=1
   parts.append('<table>')
   for idx,row in enumerate(rows):
    if set(row.replace('|','').replace(' ','').replace(':',''))=={'-'}:continue
    tag='th' if idx==0 else 'td';parts.append('<tr>'+''.join(f'<{tag}>{txt(c.strip())}</{tag}>' for c in row.strip('|').split('|'))+'</tr>')
   parts.append('</table>');continue
  elif line.startswith('>'):parts.append('<p class="note">'+txt(line[1:].strip())+'</p>')
  elif line.strip():parts.append('<p>'+txt(line)+'</p>')
  i+=1
 if section:parts.append('</section>')
 filename=file.stem+'.html'
 (dest/filename).write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>'+css+'</style><header><small>PETSENSE AI / STRATEGY 2026</small><h1>'+title+'</h1><p>관찰에서 기록으로, 기록에서 지속적인 돌봄으로.</p></header><main><nav><a href="index.html">문서 목록</a><a href="'+file.name+'">편집용 원본</a></nav>'+''.join(parts)+'</main><footer>2026-10-28 · v6 · 구현/제안/수치 가정 구분 · 인쇄 가능</footer></html>')
 links.append((filename,title))
(dest/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PetSense AI 실행계획</title><style>'+css+'</style><header><small>PETSENSE AI / NEXT CHAPTER</small><h1>전국 보호자를 위한<br>관찰·기록 서비스의 성장 계획</h1><p>사업 · 제품 · 개발 / 실행안 v6</p></header><main><section><h2>이번 산출물</h2><p>사업 가정과 실제 구현 상태를 구분한 3종 계획서와 실행 TODO. <a href="TODO.md">현재 TODO</a> · <a href="IMPLEMENTATION_PLAN.md">구현 계획</a> · <a href="QA.json">검증 기록</a>. 문서는 브라우저 인쇄로 PDF 저장할 수 있습니다.</p><nav>'+''.join('<a href="'+n+'">'+t+'</a>' for n,t in links)+'</nav></section><section><h2>앱 개발 현황</h2><p>녹음·음성 파일 선택 → 구간 변환 → 소리 점수 → 상황 기록 → 최근7일 요약·상담 노트·삭제. 프로젝트 서버를 실행한 뒤 /app에서 확인합니다.</p><p>고정 AST 가중치·합성 입력·Linux Chromium에서 계정 인증/독립 분석/저장/삭제를 검증했습니다. 상세 커밋과 실행은 QA.json을 확인하세요. 실제 개 행동 정확도·국내 PC·휴대폰 검증, 영상 제품 연결·가족 공유·전문가 연결·결제는 미완료입니다.</p></section></main></html>')
qa=json.loads((root/'artifacts/latest-verification.json').read_text()) if (root/'artifacts/latest-verification.json').exists() else {'verification':'not recorded'}
shutil.copy2(root/'tasks/todo.md',dest/'TODO.md')
shutil.copy2(root/'tasks/plan.md',dest/'IMPLEMENTATION_PLAN.md')
for name in ['NEXT_STEPS.md','LABEL_ACQUISITION.md','VIDEO_EVALUATION.md','ISOLATED_AUDIO.md','SELF_DIRECTED_PROGRESS.md','VIDEO_RESEARCH_EXPANSION.md']:
 shutil.copy2(root/'docs'/name,dest/name)
(dest/'QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
for name,source in [('PetSense_Strategy_v6_20261028.zip',True),('PetSense_App_Source_v6_20261028.zip',False)]:
 out=root/'artifacts'/name
 with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
  if source:
   for p in sorted(dest.rglob('*')):
    if p.is_file():z.write(p,p.relative_to(dest))
  else:
   for p in sorted(root.rglob('*')):
    if not p.is_file() or p.is_symlink():continue
    rel=p.relative_to(root)
    if any(x in {'.git','artifacts','data','__pycache__','node_modules'} or x.startswith('.venv') for x in rel.parts):continue
    if subprocess.run(['git','check-ignore','-q',str(rel)],cwd=root).returncode==0:continue
    if p.suffix in {'.pem','.key'} or p.name.startswith('.env') and p.name!='.env.example':continue
    z.write(p,'PetSense_AI/'+str(rel))
 with zipfile.ZipFile(out) as z:assert z.testzip() is None
 print(out.name,out.stat().st_size)
