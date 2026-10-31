"""Owner-only printable report and stale-response checks in HTTPS membership flow."""
from pathlib import Path
from playwright.sync_api import expect,Error


def report_flow(page,base,pet_id):
    for language,expected in [('en','Consultation preparation report'),('ko','상담 준비 리포트')]:
        page.goto(base+'/understand?lang='+language)
        expect(page.locator('#guide-profile option')).to_have_count(3)
        page.locator('#guide-profile').select_option(pet_id)
        page.locator('#report-load').click()
        expect(page.locator('#report-preview')).to_contain_text('Account deletion fixture')
        expect(page.locator('#report-download')).to_be_disabled()
        page.locator('#report-consent').check()
        with page.expect_download() as event:page.locator('#report-download').click()
        html=Path(event.value.path()).read_text()
        assert expected in html and 'Account deletion fixture' in html
        assert '<script' not in html and '<iframe' not in html
        expect(page.locator('#report-consent')).not_to_be_checked()
        # Download is an actual printable, self-contained document, not a JSON wrapper.
        preview=page.context.new_page()
        try:
            preview.set_content(html)
            expect(preview.locator('h1')).to_have_text(expected)
            for width in [390,1440]:
                preview.set_viewport_size({'width':width,'height':900})
                assert preview.evaluate('document.documentElement.scrollWidth<=innerWidth')
        finally:preview.close()
        page.locator('#report-consent').check();page.locator('#report-days').select_option('30')
        expect(page.locator('#report-consent')).not_to_be_checked()
        expect(page.locator('#report-preview')).to_be_empty()
    # Delay a report and switch profile; neither preview nor download may use it.
    held=[]
    pattern='**/v1/me/journal/report?*'
    page.route(pattern,lambda route:held.append(route))
    with page.expect_request(pattern):page.locator('#report-load').click()
    other=page.locator('#guide-profile option').nth(2).get_attribute('value')
    if other==pet_id:other=page.locator('#guide-profile option').nth(1).get_attribute('value')
    page.locator('#guide-profile').select_option(other)
    assert held
    try:held[0].fulfill(status=200,content_type='application/json',body='{}')
    except Error:pass
    page.unroute(pattern);page.wait_for_timeout(100)
    expect(page.locator('#report-preview')).to_be_empty()
    expect(page.locator('#report-download')).to_be_disabled()
    page.locator('#guide-profile').select_option(pet_id)
