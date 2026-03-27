"""Test double-click-to-edit for all column types on Widgets page."""
from playwright.sync_api import sync_playwright

BASE = 'http://0.0.0.0:8011'


def test_double_click_editing():
    print('\n=== TEST: Double-click editing (all column types) ===')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        js_errors = []
        page.on('pageerror', lambda err: js_errors.append(str(err)))

        page.goto(f'{BASE}/treegrid/widgets/')
        page.wait_for_selector('#widgets_tree_table')
        page.wait_for_timeout(1000)

        # Expand first company
        page.locator('.fancytree-expander').first.click()
        page.wait_for_timeout(1000)

        # Find first person row (non-folder)
        rows = page.locator('#widgets_tree_table tbody tr:not(.fancytree-folder)')
        row_count = rows.count()
        print(f'  Person rows found: {row_count}')
        if row_count == 0:
            print('  FAIL: No person rows')
            browser.close()
            return

        first_row = rows.first
        tds = first_row.locator('td')
        td_count = tds.count()
        print(f'  Columns in first person row: {td_count}')

        # Column 0: Name (tree column, read-only)
        # Column 1: First Name (text, double-click to edit)
        # Column 2: Active (checkbox, inline:false - shows tick/empty)
        # Column 3: Title (select, inline:false - shows text)
        # Column 4: Importance (select, inline:false - shows text)
        # Column 5: Age (read-only)

        # Check Active column shows as text/icon, NOT a checkbox widget
        active_td = tds.nth(2)
        has_checkbox = active_td.locator('input[type="checkbox"]').count()
        active_text = active_td.inner_html()
        print(f'  Active cell - has checkbox widget: {has_checkbox > 0}, html: "{active_text[:60]}"')

        # Check Title column shows as text, NOT a select widget
        title_td = tds.nth(3)
        has_select = title_td.locator('select').count()
        title_text = title_td.inner_text()
        print(f'  Title cell - has select widget: {has_select > 0}, text: "{title_text}"')

        # Double-click First Name (text edit)
        fname_td = tds.nth(1)
        fname_text = fname_td.inner_text()
        print(f'\n  Double-click First Name (current: "{fname_text}")')
        fname_td.dblclick()
        page.wait_for_timeout(300)
        has_input = fname_td.locator('input[type="text"]').count()
        print(f'  Text input appeared: {has_input > 0}')

        # Press Escape to cancel
        page.keyboard.press('Escape')
        page.wait_for_timeout(300)

        # Double-click Active (checkbox toggle)
        print(f'\n  Double-click Active cell')
        active_before = active_td.inner_html()
        active_td.dblclick()
        page.wait_for_timeout(500)
        active_after = active_td.inner_html()
        print(f'  Before: "{active_before[:40]}" -> After: "{active_after[:40]}"')
        changed = active_before != active_after
        print(f'  Changed: {changed}')

        # Double-click Title (select dropdown)
        print(f'\n  Double-click Title cell')
        title_td.dblclick()
        page.wait_for_timeout(300)
        has_select_now = title_td.locator('select').count()
        print(f'  Select appeared: {has_select_now > 0}')
        if has_select_now > 0:
            # Change the value
            title_td.locator('select').select_option(label='Mrs')
            page.wait_for_timeout(500)
            title_after = title_td.inner_text()
            print(f'  After selecting Mrs: "{title_after}"')

        # Double-click Importance (select dropdown)
        imp_td = tds.nth(4)
        print(f'\n  Double-click Importance cell (current: "{imp_td.inner_text()}")')
        imp_td.dblclick()
        page.wait_for_timeout(300)
        has_imp_select = imp_td.locator('select').count()
        print(f'  Select appeared: {has_imp_select > 0}')

        if js_errors:
            print(f'\n  JS ERRORS:')
            for err in js_errors:
                print(f'    {err[:200]}')
        else:
            print('\n  No JS errors!')

        browser.close()


if __name__ == '__main__':
    test_double_click_editing()
