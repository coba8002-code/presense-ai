"""Plan goal -> new followup -> guardian-confirmed completion -> delete."""
from playwright.sync_api import expect


def plans_flow(page,base,pet_id):
    page.goto(base+'/understand?lang=en')
    expect(page.locator('#guide-profile option')).to_have_count(3)
    page.locator('#guide-profile').select_option(pet_id);page.locator('#journal-load').click()
    expect(page.locator('#journal-list article')).to_have_count(1)
    page.locator('#journal-list button').click();expect(page.locator('#plans')).to_be_visible()
    expect(page.locator('#plan-create')).to_be_enabled()
    page.locator('#plan-goal').fill('<img src=x onerror=alert(1)> Observe from a safe distance')
    page.locator('#plan-consent').check();page.locator('#plan-create').click()
    expect(page.locator('#plan-list article')).to_have_count(1)
    assert page.locator('#plan-list img').count()==0
    expect(page.locator('#plan-list select option')).to_have_count(1) # Older followup cannot close this plan.
    page.locator('#follow-what').fill('New observation for plan completion')
    page.locator('#follow-consent').check();page.locator('#follow-save').click()
    expect(page.locator('#followup-list article')).to_have_count(2)
    expect(page.locator('#plan-list select option')).to_have_count(2)
    page.locator('#plan-list select').select_option(index=1)
    page.once('dialog',lambda dialog:dialog.accept())
    page.get_by_role('button',name='Confirm completion with followup',exact=True).click()
    expect(page.locator('#plan-list')).to_contain_text('Completed · guardian confirmation')
    page.goto(base+'/understand?lang=ko')
    expect(page.locator('#guide-profile option')).to_have_count(3)
    page.locator('#guide-profile').select_option(pet_id);page.locator('#journal-load').click()
    expect(page.locator('#journal-list article')).to_have_count(1);page.locator('#journal-list button').click()
    expect(page.locator('#plan-list')).to_contain_text('완료 · 보호자 확인')
    page.once('dialog',lambda dialog:dialog.accept());page.get_by_role('button',name='계획 삭제',exact=True).click()
    expect(page.locator('#plan-list article')).to_have_count(0)
    expect(page.locator('#followup-list article')).to_have_count(2)
    # Leave a plan for the outer password-confirmed account deletion check.
    page.locator('#plan-goal').fill('Account deletion plan fixture')
    page.locator('#plan-consent').check();page.locator('#plan-create').click()
    expect(page.locator('#plan-list article')).to_have_count(1)
    page.locator('#guide-profile').select_option('')
    expect(page.locator('#plans')).to_be_hidden()
    assert page.locator('#plan-goal').input_value()==''
