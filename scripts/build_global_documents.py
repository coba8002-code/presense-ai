"""Render the global product/research/development plans as local HTML and PDFs.

Uses existing optional Playwright/Chromium tooling. No network sources or models
are called while rendering; the Markdown files retain source links and limits.
"""
import argparse
import html
from pathlib import Path
import re
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
CSS='''
:root{font-family:"Noto Sans CJK KR",system-ui,sans-serif;color:#173d42;background:#f2f5ee}*{box-sizing:border-box}body{margin:0}header{background:#173f43;color:white;padding:55px max(5vw,30px)}header small{color:#ccdea8;letter-spacing:3px}h1{font-size:36px;line-height:1.5;max-width:1000px;margin:20px 0}header p{color:#e4ebd9}main{max-width:1150px;margin:auto;padding:30px}section{background:white;border-radius:16px;padding:28px;margin-bottom:24px}h2{color:#137b77;font-size:23px;margin-top:30px;line-height:1.6}p,li{font-size:14px;line-height:1.95}a{color:#14736f;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;table-layout:fixed;font-size:12px;line-height:1.8;margin:18px 0}td,th{padding:12px;border-bottom:1px solid #dce5d9;text-align:left;vertical-align:top;word-break:keep-all;overflow-wrap:anywhere}th{background:#137b77;color:white}th a{color:white}tr:nth-child(even){background:#f0f5eb}pre{white-space:pre-wrap;font-size:11px;line-height:1.7;background:#edf3e8;padding:18px;border-radius:10px}.flow{display:flex;gap:10px;flex-wrap:wrap;margin:25px 0}.flow span{background:#edf3e1;color:#1c5a53;padding:16px;border-radius:12px;font-size:12px;flex:1 1 170px}.navigation{display:flex;gap:12px;flex-wrap:wrap}.navigation a{padding:10px 16px;border:1px solid #cbd9ca;background:white;border-radius:8px;text-decoration:none}.version{font-size:11px;color:#62796c}.cover-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.cover-summary div{background:#edf3e1;padding:25px;border-radius:14px}.cover-summary strong{display:block;color:#1a645c;margin-bottom:10px}img{max-width:100%}@media(max-width:700px){main{padding:16px}section{padding:20px}h1{font-size:27px}.cover-summary{grid-template-columns:1fr}table{font-size:11px}td,th{padding:7px}}@media print{@page{size:A4;margin:20mm 16mm}body{background:white}header{background:white;color:#173f43;padding:0 0 14px;border-bottom:3px solid #137b77}header small,header p{color:#40665d}h1{font-size:24pt;line-height:1.5}main{max-width:none;padding:0}section{padding:0;border:0;border-radius:0;margin:0}h2{font-size:14pt;break-after:avoid;margin-top:18px}p,li{font-size:9.4pt;line-height:1.85}table{font-size:8pt;line-height:1.75}td,th{padding:7px}tr{break-inside:avoid}pre{font-size:8pt}.navigation{display:none}.flow span{font-size:8pt;padding:9px}.version{font-size:8pt}}
'''


def inline(text):
    value=html.escape(text)
    value=re.sub(r'\[([^\]]+)\]\((https://[^\s)]+|[A-Za-z0-9_./-]+\.md)\)',r'<a href="\2">\1</a>',value)
    return re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',value)


def markdown(text):
    lines=text.splitlines();parts=[];i=1
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('```'):
            diagram=line=='```mermaid';code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):code.append(lines[i]);i+=1
            if diagram:
                labels=list(dict.fromkeys(re.findall(r'\w+\[([^\]]+)\]', '\n'.join(code))))
                parts.append('<div class="flow">'+''.join('<span>'+str(n+1)+' / '+html.escape(label)+'</span>' for n,label in enumerate(labels))+'</div>')
            else:parts.append('<pre>'+html.escape('\n'.join(code))+'</pre>')
        elif line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=lines[i].strip();i+=1
                if set(row.replace('|','').replace(' ','').replace(':',''))=={'-'}:continue
                rows.append(row.strip('|').split('|'))
            parts.append('<table>'+''.join('<tr>'+''.join('<'+('th' if n==0 else 'td')+'>'+inline(cell.strip())+'</'+('th' if n==0 else 'td')+'>' for cell in row)+'</tr>' for n,row in enumerate(rows))+'</table>');continue
        elif line.startswith('## '):parts.append('<h2>'+inline(line[3:])+'</h2>')
        else:parts.append('<p>'+inline(line)+'</p>')
        i+=1
    return ''.join(parts)


def shell(title,body,cover=False):
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><style>'+CSS+'</style><header><small>PETSENSE AI / GLOBAL COMPANION</small><h1>'+html.escape(title)+'</h1><p>이해하고 · 돌보고 · 함께 즐기고 · 연결되다</p></header><main><section><p class="version">2026.10.31 KST / 확인 사실 · 제안 · 검증 목표 구분 / 현재 세계1위·행동 정확도·운영 출시 보증 아님</p>'+('' if cover else '<nav class="navigation"><a href="index.html">문서 목록</a></nav>')+body+'</section></main></html>'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--chromium',type=Path)
    parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args();out=args.output_dir
    out.mkdir(parents=True,exist_ok=False);documents=[]
    for source in sorted((ROOT/'docs/global-20261031').glob('*.md')):
        shutil.copy2(source,out/source.name);title=source.read_text().splitlines()[0].lstrip('# ')
        target=out/(source.stem+'.html');target.write_text(shell(title,markdown(source.read_text())))
        documents.append((target,title))
    links=''.join('<p><a href="'+path.name+'">'+html.escape(title)+'</a> / <a href="'+path.stem+'.pdf">PDF</a> / <a href="'+path.stem+'.md">MD</a></p>' for path,title in documents)
    (out/'index.html').write_text(shell('우리 개를 이해하는 일상에서, 전 세계 보호자의 동반자로', '<div class="cover-summary"><div><strong>WHY US</strong>내 개의 맥락에서 시작하는 이해</div><div><strong>TRUST</strong>독립 평가와 근거로 쌓는 신뢰</div><div><strong>TOGETHER</strong>작은 돌봄과 즐거움, 사람 연결</div></div><h2>3종 실행 문서</h2>'+links+'<p>상황 카드는 보호자 진술이며 원인/의도에 대한 AI 분석이나 학습 정답이 아닙니다. 한국어/영어 일부 흐름·계정/큐 베타를 구현했으며 가족/전문가/커뮤니티는 후속입니다.</p>',cover=True))
    for name in ['WEB_MEMBERSHIP.md','WEB_AUTH_SPEC.md','PRIVACY_MAINTENANCE.md','NEXT_STEPS.md']:
        shutil.copy2(ROOT/'docs'/name,out/name)
    shutil.copy2(ROOT/'tasks/todo.md',out/'TODO.md')
    if args.screenshots:shutil.copytree(args.screenshots,out/'screenshots')
    with sync_playwright() as pw:
        options={'executable_path':str(args.chromium)} if args.chromium else {}
        browser=pw.chromium.launch(**options)
        try:
            page=browser.new_page()
            page.route('https://**/*',lambda route:route.abort())
            for target,title in documents:
                page.set_content(target.read_text());page.emulate_media(media='print')
                page.pdf(path=str(target.with_suffix('.pdf')),format='A4',print_background=True,
                    display_header_footer=True,header_template='<span></span>',
                    footer_template='<div style="font-size:8px;color:#61766c;width:100%;text-align:center">PetSense AI / GLOBAL STRATEGY / 2026.10.31 — <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
                    margin={'top':'20mm','bottom':'20mm','left':'16mm','right':'16mm'})
        finally:browser.close()
    print('Global plans rendered as local HTML/PDF. No model or source-network calls.')


if __name__=='__main__':main()
