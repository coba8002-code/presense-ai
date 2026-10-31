"""Two independent HTTPS cookie contexts exercise consented journal sharing."""
import secrets
from playwright.sync_api import expect


def care_flow(owner,base,pet_id):
    owner.locator('#care-consent').check();owner.locator('#care-create').click()
    expect(owner.locator('#care-secret code')).to_be_visible()
    code=owner.locator('#care-secret code').text_content()
    assert len(code)==43
    context=owner.context.browser.new_context()
    reader=context.new_page();errors=[];reader.on('pageerror',lambda error:errors.append(str(error)))
    password=secrets.token_urlsafe(24)
    try:
        reader.goto(base+'/auth')
        status=reader.evaluate("""async password=>{
          const r=await fetch('/v1/auth/signup',{method:'POST',headers:{'Content-Type':'application/json','X-PetSense-Request':'web'},body:JSON.stringify({email:'care-reader@example.invalid',password,accept_terms:true,accept_privacy:true,terms_version:'test-v1',privacy_version:'test-v1'})});return r.status;
        }""",password)
        assert status==201
        reader.goto(base+'/understand?lang=en')
        expect(reader.locator('#care-accept')).to_be_enabled()
        reader.locator('#care-code').fill(code);reader.locator('#care-consent').check();reader.locator('#care-accept').click()
        expect(reader.locator('#care-received article')).to_have_count(1)
        assert reader.locator('#care-code').input_value()==''
        reader.locator('#care-received button').first.click()
        expect(reader.locator('#care-cases article')).to_have_count(1)
        reader.locator('#care-cases button').first.click()
        expect(reader.locator('#care-detail')).to_contain_text('Account deletion fixture')
        assert reader.locator('#care-detail img,#care-detail script').count()==0
        owner.locator('#care-load').click()
        expect(owner.locator('#care-sent article')).to_have_count(1)
        owner.once('dialog',lambda dialog:dialog.accept());owner.locator('#care-sent button').click()
        expect(owner.locator('#care-sent article')).to_have_count(0)
        reader.locator('#care-load').click()
        expect(reader.locator('#care-received article')).to_have_count(0)
        expect(reader.locator('#care-detail')).to_be_empty()
        # Recreate and leave a grant to prove account deletion removes access.
        owner.locator('#care-consent').check();owner.locator('#care-create').click()
        expect(owner.locator('#care-secret code')).to_be_visible()
        code=owner.locator('#care-secret code').text_content()
        reader.locator('#care-code').fill(code);reader.locator('#care-consent').check();reader.locator('#care-accept').click()
        expect(reader.locator('#care-received article')).to_have_count(1)
        status=reader.evaluate("async password=>{await PetSenseGuide.api('/v1/auth/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password})});return true}",password)
        assert status
        owner.locator('#care-load').click();expect(owner.locator('#care-sent article')).to_have_count(0)
        assert not errors
    finally:
        context.close()
