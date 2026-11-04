"""Synthetic journal assertions within the existing HTTPS membership smoke."""
import json
from pathlib import Path
from playwright.sync_api import expect, Error


def journal_flow(page,base,pet_id,screenshots=None):
    page.locator('#retention-days').select_option('90')
    page.locator('#storage-consent').check();page.locator('#save-case').click()
    expect(page.locator('#guide-status')).to_contain_text('Case saved to your journal')
    expect(page.locator('#journal-detail')).to_be_visible()
    assert page.locator('#journal-context img').count()==0
    expect(page.locator('#journal-summary')).to_contain_text('Case records: 1')
    expect(page.locator('#journal-summary')).to_contain_text('Insufficient history')
    expect(page.locator('#journal-summary')).to_contain_text('not actual vocalization/movement rates')
    expect(page.locator('#journal-summary')).to_contain_text('Cases without a followup: 1')
    page.locator('#journal-window').select_option('30')
    expect(page.locator('#journal-window')).to_be_enabled()
    page.locator('#follow-action').select_option('give_space')
    page.locator('#follow-what').fill('<b>Gave space</b>')
    page.locator('#follow-outcome').select_option('unknown')
    page.locator('#follow-note').fill('Synthetic observation, not a measured training effect')
    page.locator('#follow-consent').check();page.locator('#follow-save').click()
    expect(page.locator('#followup-list article')).to_have_count(1)
    assert page.locator('#followup-list b').count()==0
    expect(page.locator('#journal-summary')).to_contain_text('Cases without a followup: 0')
    with page.expect_download() as observed:page.locator('#journal-export').click()
    exported=json.loads(Path(observed.value.path()).read_text())
    case=exported['case'];case_id=case['id']
    assert case['data']['retention_days']==90 and len(case['followups'])==1
    assert not case['model_analysis'] and not case['training_approved'] and 'owner' not in case
    if screenshots:
        screenshots.mkdir(parents=True,exist_ok=False)
        for width in [390,1440]:
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#journal').screenshot(path=str(screenshots/f'en-{width}.png'))
    page.goto(base+'/understand?lang=ko')
    expect(page.locator('#guide-profile option')).to_have_count(2)
    page.locator('#guide-profile').select_option(pet_id);page.locator('#journal-load').click()
    expect(page.locator('#journal-list article')).to_have_count(1)
    expect(page.locator('#journal-summary')).to_contain_text('상황 기록: 1')
    expect(page.locator('#journal-summary')).to_contain_text('기록 기준선 미충족')
    page.locator('#journal-list button').click()
    expect(page.locator('#followup-list article')).to_have_count(1)
    if screenshots:
        for width in [390,1440]:
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.locator('#journal').screenshot(path=str(screenshots/f'ko-{width}.png'))
    other=page.evaluate("async()=>PetSenseGuide.api('/v1/me/pets',{method:'POST',headers:{'Content-Type':'application/json','X-Storage-Consent':'true'},body:JSON.stringify({name:'Other synthetic dog'})})")
    page.locator('#profiles-refresh').click();expect(page.locator('#guide-profile option')).to_have_count(3)
    page.locator('#guide-profile').select_option(pet_id);page.locator('#journal-load').click()
    expect(page.locator('#journal-list article')).to_have_count(1)
    held=[]
    page.route('**/v1/me/journal/'+case_id,lambda route:held.append(route))
    with page.expect_request('**/v1/me/journal/'+case_id):page.locator('#journal-list button').click()
    page.locator('#guide-profile').select_option(other['id'])
    assert held
    try:held[0].fulfill(status=200,content_type='application/json',body=json.dumps(case))
    except Error:pass  # Aborting the old fetch may already have closed its route.
    page.unroute('**/v1/me/journal/'+case_id)
    page.wait_for_timeout(100)
    expect(page.locator('#journal-detail')).to_be_hidden();expect(page.locator('#journal-list article')).to_have_count(0)
    page.locator('#guide-profile').select_option(pet_id);page.locator('#journal-load').click()
    expect(page.locator('#journal-list article')).to_have_count(1);page.locator('#journal-list button').click()
    expect(page.locator('#journal-detail')).to_be_visible()
    page.once('dialog',lambda dialog:dialog.accept());page.locator('#journal-delete').click()
    expect(page.locator('#journal-status')).to_contain_text('삭제했습니다')
    expect(page.locator('#journal-detail')).to_be_hidden();expect(page.locator('#journal-list article')).to_have_count(0)
    # Leave a fresh case/followup to prove later password-confirmed account deletion.
    page.locator('#behavior').select_option('barking');page.locator('#before').fill('Account deletion fixture')
    page.locator('#case-form button').click();page.locator('#storage-consent').check();page.locator('#save-case').click()
    expect(page.locator('#journal-detail')).to_be_visible()
    page.locator('#follow-what').fill('Synthetic followup');page.locator('#follow-consent').check();page.locator('#follow-save').click()
    expect(page.locator('#followup-list article')).to_have_count(1)
