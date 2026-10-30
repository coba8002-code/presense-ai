"""Public beta account screens; operator-supplied policy metadata, no third-party assets."""
import html
from pathlib import Path
from fastapi import APIRouter,HTTPException
from fastapi.responses import HTMLResponse,Response
from backend.web_security import settings

router=APIRouter()
HEADERS={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
    'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
    'Permissions-Policy':'microphone=(), camera=(), geolocation=()'}

def asset(name):
    files={'':('index.html','text/html'),'auth.js':('auth.js','text/javascript'),'auth.css':('auth.css','text/css')}
    if name not in files:raise HTTPException(404,'Not found')
    filename,mime=files[name]
    return Response((Path(__file__).parent/'static/auth'/filename).read_text(),media_type=mime,headers=HEADERS)

@router.get('/auth')
async def account_page():return asset('')

@router.get('/auth/policy')
async def policy():
    cfg=settings()
    if not cfg:raise HTTPException(503,'Account policy not configured')
    values={key:html.escape(value) for key,value in cfg.items()}
    body=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PetSense AI 베타 이용 안내</title><link rel="stylesheet" href="/app/app.css"><main><section class="panel"><a href="/auth">← 계정 화면</a><h1>베타 이용·개인정보 안내</h1><p>운영자: {values['operator']} / 문의: {values['contact']}</p><p>제한 베타용 안내이며 공개 운영 법률 검토·보안 심사 완료를 뜻하지 않습니다.</p><h2 id="terms">이용 안내 · {values['terms_version']}</h2><p>개 전용 소리 관찰·상황 기록 도구입니다. 감정·원인·교정 효과나 수의학적 진단을 확정하지 않습니다. 이상이 의심되면 전문가에게 상담하세요. 현재 이 계정 기능은 유료 결제·이메일 확인·소셜 로그인을 제공하지 않습니다.</p><p>이메일은 로그인 식별자입니다. 소유 확인 표시를 하지 않습니다. 비밀번호는 15~128자이며 복구 코드는 가입·변경·복구 때 한 번만 제공합니다. 코드를 별도로 보관해야 하며 코드와 비밀번호를 모두 분실한 경우 자동 이메일 복구가 없습니다.</p><h2 id="privacy">개인정보 안내 · {values['privacy_version']}</h2><p>계정 유지에 이메일·비밀번호 해시/salt·복구코드 해시·동의 버전/시각·세션 해시를 처리하고 탈퇴 시 삭제합니다. 비밀번호·세션·복구코드 원문을 DB에 보관하지 않습니다. 보안 요청 제한용 식별자/연결주소 해시 bucket은 최대24시간 정리 규칙을 적용하며 익명 정보라고 주장하지 않습니다.</p><p>프로필/메모는 별도 동의부터30일, 분석 작업 원본은 최대15분 기한과 완료·실패·취소 시 조기 제거, 결과/최소 작업 기록은 등록부터24시간 기한입니다. 실제 정리는 접근·worker/운영 정리 작업이 실행돼야 진행됩니다. 원본 임시 보관은 별도 동의가 필요하고 학습 동의로 확대하지 않습니다.</p><p>HTTPS의 HttpOnly·Secure·SameSite=Strict 쿠키로 최대24시간 로그인합니다. 로그아웃은 현재 세션, 복구/비밀번호 변경은 기존 모든 세션을 철회합니다. 서버 프로필/메모/작업·사용량·계정은 현재 비밀번호를 재확인한 탈퇴로 삭제합니다. 별도 브라우저 기록·다운로드한 파일은 해당 기기에서 지워야 합니다.</p><p>국내 운영 저장소·백업·정기 삭제·메일·소셜/외부 분석의 운영 설정과 검토는 별도입니다. 추가 공급자 전송은 해당 연동의 동의를 따라야 하며 이 베타 계정 기능이 외부 전송을 자동 활성화하지 않습니다.</p></section></main></html>'''
    return HTMLResponse(body,headers=HEADERS)

@router.get('/auth/{name}')
async def auth_asset(name:str):return asset(name)
