"""Browser tests for treegrid batch save and column filters using Playwright."""
import sys
from playwright.sync_api import sync_playwright

BASE = 'http://0.0.0.0:8011'


def test_batch_save():
    """Test: tick a checkbox, verify Save button enables, click Save, verify toast."""
    print('\n=== TEST: Batch Save ===')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Collect console messages and errors
        console_msgs = []
        page.on('console', lambda msg: console_msgs.append(f'{msg.type}: {msg.text}'))
        js_errors = []
        page.on('pageerror', lambda err: js_errors.append(str(err)))

        page.goto(f'{BASE}/treegrid/batch/')
        page.wait_for_selector('#batch_tree_table')
        page.wait_for_timeout(1000)  # Let fancytree render

        # Check Save button is disabled initially
        save_btn = page.locator('#batch_tree_save_btn')
        is_disabled = save_btn.is_disabled()
        print(f'  Save button initially disabled: {is_disabled}')
        assert is_disabled, 'Save button should be disabled initially'

        # Check changes counter is empty
        changes_text = page.locator('#batch_tree_changes').inner_text()
        print(f'  Changes text initially: "{changes_text}"')

        # Expand first company node
        expanders = page.locator('.fancytree-expander')
        if expanders.count() > 0:
            expanders.first.click()
            page.wait_for_timeout(1000)  # Wait for lazy load
            print(f'  Expanded first node, expanders now: {expanders.count()}')

        # Find a checkbox
        checkboxes = page.locator('.treegrid-checkbox')
        cb_count = checkboxes.count()
        print(f'  Checkboxes found: {cb_count}')

        if cb_count > 0:
            # Tick the first checkbox
            checkboxes.first.click()
            page.wait_for_timeout(500)

            # Check Save button is now enabled
            is_disabled_after = save_btn.is_disabled()
            print(f'  Save button disabled after tick: {is_disabled_after}')

            changes_text_after = page.locator('#batch_tree_changes').inner_text()
            print(f'  Changes text after tick: "{changes_text_after}"')

            if not is_disabled_after:
                # Click Save
                save_btn.click()
                page.wait_for_timeout(2000)

                # Check for toast
                toast = page.locator('.toast-body, .toast')
                toast_count = toast.count()
                print(f'  Toast elements found: {toast_count}')
                if toast_count > 0:
                    toast_text = toast.first.inner_text()
                    print(f'  Toast text: "{toast_text[:100]}"')
                else:
                    print('  NO TOAST FOUND')

                # Check changes counter is cleared
                changes_final = page.locator('#batch_tree_changes').inner_text()
                print(f'  Changes text after save: "{changes_final}"')
            else:
                print('  FAIL: Save button still disabled after ticking checkbox!')
        else:
            print('  No checkboxes found - need to expand a node first')

        # Report JS errors
        if js_errors:
            print(f'\n  JS ERRORS:')
            for err in js_errors:
                print(f'    {err}')

        if console_msgs:
            errors = [m for m in console_msgs if m.startswith('error')]
            if errors:
                print(f'\n  Console errors:')
                for m in errors:
                    print(f'    {m}')

        browser.close()


def test_full_column_filter():
    """Test: type in column filter, clear it, check for JS errors."""
    print('\n=== TEST: Column Filters (Full Featured) ===')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        js_errors = []
        page.on('pageerror', lambda err: js_errors.append(str(err)))

        page.goto(f'{BASE}/treegrid/full/')
        page.wait_for_selector('#full_tree_table')
        page.wait_for_timeout(1000)

        # Find column filter inputs
        filters = page.locator('.treegrid-col-filter')
        filter_count = filters.count()
        print(f'  Column filters found: {filter_count}')

        # Expand a node first
        expanders = page.locator('.fancytree-expander')
        if expanders.count() > 0:
            expanders.first.click()
            page.wait_for_timeout(1000)

        # Type in the first text filter (Group/Name column)
        text_filters = page.locator('input.treegrid-col-filter')
        if text_filters.count() > 0:
            text_filters.first.fill('test')
            page.wait_for_timeout(500)
            print(f'  Typed "test" in first filter, JS errors so far: {len(js_errors)}')

            # Now try the boolean column filter (Active column)
            # Find all text input filters
            for i in range(text_filters.count()):
                col_idx = text_filters.nth(i).get_attribute('data-col-idx')
                print(f'  Text filter {i}: col-idx={col_idx}')

            # Type in the Active column filter (should be col-idx 2 for is_active)
            active_filter = page.locator('input.treegrid-col-filter[data-col-idx="2"]')
            if active_filter.count() > 0:
                active_filter.fill('true')
                page.wait_for_timeout(500)
                print(f'  Typed "true" in Active filter, JS errors: {len(js_errors)}')

                # Now try to clear it
                active_filter.fill('')
                page.wait_for_timeout(500)
                print(f'  Cleared Active filter, JS errors: {len(js_errors)}')

                # Try to clear the first filter too
                text_filters.first.fill('')
                page.wait_for_timeout(500)
                print(f'  Cleared first filter, JS errors: {len(js_errors)}')
            else:
                print('  No Active column text filter found (might be a select)')

        if js_errors:
            print(f'\n  JS ERRORS:')
            for err in js_errors:
                print(f'    {err[:200]}')
        else:
            print('  No JS errors!')

        browser.close()


if __name__ == '__main__':
    test_batch_save()
    test_full_column_filter()
