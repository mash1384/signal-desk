"""Isolated browser readiness check: launch, visit a blank page, close. No installs."""
import argparse
import os
from playwright.sync_api import sync_playwright


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--channel', default='chromium' if os.environ.get('CI') else 'chrome')
    args = p.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({} if args.channel == 'chromium' else {'channel': args.channel}))
        try:
            page = browser.new_page()
            page.goto('about:blank')
            page.close()
        finally:
            browser.close()
    print('browser readiness passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
