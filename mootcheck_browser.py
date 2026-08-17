from playwright.sync_api import sync_playwright
import re

SESSION_FILE = "instagram_session.json"
USERNAME = "mattsarap__"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    context = browser.new_context(
        storage_state=SESSION_FILE
    )

    page = context.new_page()

    page.goto(
        f"https://www.instagram.com/{USERNAME}/",
        wait_until="domcontentloaded"
    )

    page.wait_for_timeout(3000)

    print("\n=== INSTAGRAM FOLLOWERS / FOLLOWING ===\n")

    # Instagram currently uses href="#" for the Followers/Following
    # buttons, so identify them by their visible text instead.

    followers_button = page.get_by_text(
        re.compile(r"[\d,]+\s+followers", re.IGNORECASE)
    ).first

    following_button = page.get_by_text(
        re.compile(r"[\d,]+\s+following", re.IGNORECASE)
    ).first

    try:
        print("Followers button:", followers_button.inner_text())
    except Exception:
        print("Followers button: NOT FOUND")

    try:
        print("Following button:", following_button.inner_text())
    except Exception:
        print("Following button: NOT FOUND")

    print("\n=== TESTING FOLLOWERS BUTTON ===")

    try:
        followers_button.wait_for(timeout=10000)
        followers_button.click()

        page.wait_for_timeout(2000)

        print("Followers button clicked successfully.")
        print("Current URL:", page.url)

    except Exception as e:
        print("Could not click Followers button:")
        print(e)

    print("\nBrowser is open so you can inspect the page.")
    input("Press ENTER to close...")
    

    browser.close()