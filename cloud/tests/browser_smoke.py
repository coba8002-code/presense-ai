"""Browser contract test with SYNTHETIC intercepted Auth/REST responses.
Not evidence of live Supabase email, RLS, deployment, or model accuracy.
"""
import base64
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

origin = 'http://127.0.0.1:5174'
uid = '10000000-0000-4000-8000-000000000001'
user = {'id': uid, 'email': 'synthetic@example.test', 'aud': 'authenticated', 'role': 'authenticated', 'app_metadata': {}, 'user_metadata': {}}
def b64(value):
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
token = b64({'alg':'HS256','typ':'JWT'})+'.'+b64({'sub':uid,'role':'authenticated','aud':'authenticated','session_id':'20000000-0000-4000-8000-000000000001','exp':int(time.time())+3600})+'.synthetic'
store = {name: [] for name in ['accounts','dogs','notes','requests','plans']}
calls = []

def route_api(route):
    req = route.request
    calls.append((req.method, req.url))
    headers = {'access-control-allow-origin': origin, 'access-control-allow-headers':'authorization,apikey,content-type,x-client-info,prefer,x-supabase-api-version', 'access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS', 'content-type':'application/json'}
    if req.method == 'OPTIONS':
        route.fulfill(status=204, headers=headers); return
    path = req.url.split('.supabase.co')[-1].split('?')[0]
    if path == '/auth/v1/token':
        body = {'access_token': token, 'refresh_token':'synthetic-refresh', 'expires_in':3600, 'token_type':'bearer','user':user}
    elif path == '/auth/v1/user': body = user
    elif path == '/auth/v1/logout':
        route.fulfill(status=204, headers=headers); return
    elif path == '/rest/v1/rpc/ps_session_active': body = True
    elif path.startswith('/rest/v1/ps_'):
        table = path.removeprefix('/rest/v1/ps_')
        data = store[table]
        if req.method == 'POST':
            row = json.loads(req.post_data)
            row.update({'id':row.get('id',str(len(data)+1)), 'owner':uid,'created_at':'2026-11-04T00:00:00Z'})
            if table == 'requests': row['status']='awaiting_model'
            data.append(row)
            body = row if 'application/vnd.pgrst.object+json' in req.headers.get('accept','') else [row]
        elif req.method == 'PATCH':
            selected = req.url.split('id=eq.')[-1].split('&')[0]
            for row in data:
                if row['id'] == selected: row.update(json.loads(req.post_data))
            body = None
        elif req.method == 'DELETE':
            selected = req.url.split('id=eq.')[-1].split('&')[0]
            store[table] = [row for row in data if row['id']!=selected]
            body = None
        else: body = data
    else: raise AssertionError('Unexpected external request: '+path)
    route.fulfill(status=200, headers=headers, body=json.dumps(body,ensure_ascii=False))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://*.supabase.co/**',route_api)
    page.goto(origin)
    page.wait_for_load_state('networkidle')
    expect(page.locator('#auth-area')).to_be_visible()
    Path('artifacts/cloud-beta').mkdir(parents=True,exist_ok=True)
    page.screenshot(path='artifacts/cloud-beta/welcome-desktop.png',full_page=True)
    page.locator('#email').fill('synthetic@example.test')
    page.locator('#password').fill('synthetic-password-only')
    page.locator('#auth-submit').click()
    expect(page.locator('#onboarding')).to_be_visible()
    page.locator('#account-consent').check()
    page.locator('#accept-account').click()
    expect(page.locator('#workspace')).to_be_visible()
    page.locator('#toggle-dog').click()
    page.locator('#dog-form [name=name]').fill('<img src=x onerror=alert(1)>')
    page.locator('#dog-form [name=consent]').check()
    page.locator('#dog-form button').click()
    expect(page.locator('#dog-count')).to_have_text('1')
    assert page.locator('#dog-list img').count()==0, 'Untrusted name must be text'
    page.locator('[data-tab=observe]').click()
    page.locator('#observe-form [name=context]').fill('초인종 이후 세 번 짖었어요. 합성 화면 검사용 기록입니다.')
    page.locator('#observe-form [name=consent]').check()
    page.locator('button[value=request]').click()
    expect(page.locator('#request-list')).to_contain_text('모델 연결 대기')
    page.get_by_role('button',name='요청 취소',exact=True).click()
    expect(page.locator('#request-list')).to_contain_text('취소됨')
    page.locator('#observe-form [name=context]').fill('산책 준비 중 꼬리를 흔들었다. 합성 관찰 노트.')
    page.locator('#observe-form [name=consent]').check()
    page.locator('button[value=note]').click()
    expect(page.locator('#note-count')).to_have_text('1')
    page.locator('[data-tab=care]').click()
    page.locator('#plan-form [name=title]').fill('합성 검사용 산책 계획')
    page.locator('#plan-form [name=consent]').check()
    page.locator('#plan-form button').click()
    expect(page.locator('#plan-count')).to_have_text('1')
    page.get_by_role('button',name='완료 표시',exact=True).click()
    expect(page.locator('#plan-count')).to_have_text('0')
    page.locator('[data-tab=home]').click()
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path='artifacts/cloud-beta/home-mobile-synthetic.png',full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile horizontal overflow'
    page.locator('#logout').click()
    expect(page.locator('#workspace')).to_be_hidden()
    expect(page.locator('#account-email')).to_have_text('')
    assert not errors, errors
    page.goto(origin+'/video-review/')
    page.wait_for_load_state('networkidle')
    expect(page.locator('#clip')).to_be_disabled()
    expect(page.locator('#consent')).to_be_visible()
    assert not errors,errors
    browser.close()
print(json.dumps({'browser':'chromium','synthetic_auth_rest':True,'checks':['login/onboarding','dog ownership input','escaped content','request/cancel','note','plan/completion','mobile layout','logout clearance','local video route'],'live_supabase':False,'model_calls':0,'api_calls':len(calls)}))
