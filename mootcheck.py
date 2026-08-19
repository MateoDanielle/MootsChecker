from playwright.sync_api import sync_playwright
import re
import time
import os
import sys


def collect_users(page, list_type):
    """Open an Instagram followers/following dialog and collect usernames."""

    if list_type == "followers":
        button = page.get_by_text(
            re.compile(r"[\d,]+\s+followers", re.IGNORECASE)
        ).first
    else:
        button = page.get_by_text(
            re.compile(r"[\d,]+\s+following", re.IGNORECASE)
        ).first

    print(f"\nOpening {list_type}...")

    button.wait_for(timeout=15000)
    button.click()

    page.wait_for_timeout(1500)

    dialog = page.locator('[role="dialog"]').last
    dialog.wait_for(timeout=10000)

    print("Dialog opened successfully.")
    print(f"Collecting {list_type}...")

    usernames = set()

    ignored = {
        "accounts",
        "explore",
        "direct",
        "reels",
        "stories",
        "about",
        "developer",
        "privacy",
        "terms",
    }

    stable_rounds = 0
    previous_count = 0

    for round_number in range(100):

        links = dialog.locator("a[href]")

        for i in range(links.count()):

            try:
                link = links.nth(i)
                href = link.get_attribute("href")

                if not href:
                    continue

                match = re.fullmatch(
                    r"/([A-Za-z0-9._]+)/?",
                    href
                )

                if match:

                    username = match.group(1)

                    if username.lower() not in ignored:
                        usernames.add(username)

            except Exception:
                pass

        # Scroll the largest scrollable element.
        try:

            dialog.evaluate("""
                (dialog) => {

                    const elements = [
                        dialog,
                        ...dialog.querySelectorAll('*')
                    ];

                    const scrollable = elements.filter(
                        el => el.scrollHeight > el.clientHeight + 50
                    );

                    if (scrollable.length > 0) {

                        const target = scrollable.sort(
                            (a, b) => b.scrollHeight - a.scrollHeight
                        )[0];

                        target.scrollTop = target.scrollHeight;
                    }
                }
            """)

        except Exception:
            pass

        # Give Instagram time to load more users.
        page.wait_for_timeout(700)

        current_count = len(usernames)

        if current_count == previous_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        previous_count = current_count

        # Stop after 5 scrolls without new usernames.
        if stable_rounds >= 5:

            print(
                "No new usernames found for "
                "5 consecutive scrolls."
            )
            break

        if round_number % 5 == 0:

            print(
                f"Scroll {round_number + 1:3}: "
                f"{len(usernames)} usernames"
            )

    print(
        f"Finished {list_type}: "
        f"{len(usernames)} users"
    )

    # Close dialog.
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    return usernames


def wait_for_login(page):
    """Wait for the user to complete Instagram login and verification."""

    print("\nOpening Instagram...")
    print("Please log in using the browser window.")
    print(
        "If Instagram shows a CAPTCHA or verification, "
        "complete it manually."
    )
    print(
        "MootCheck will continue automatically afterward.\n"
    )

    page.goto(
        "https://www.instagram.com/accounts/login/",
        wait_until="domcontentloaded",
        timeout=30000
    )

    print("Waiting for Instagram login/verification...")

    # Allow up to 5 minutes for login + CAPTCHA/verification.
    deadline = time.time() + 300

    while time.time() < deadline:

        try:

            current_url = page.url.lower()

            # ----------------------------------------
            # STILL IN LOGIN / VERIFICATION FLOW
            # ----------------------------------------

            if (
                "/accounts/login" in current_url
                or "/challenge/" in current_url
                or "/accounts/onetap/" in current_url
            ):

                page.wait_for_timeout(1500)
                continue

            # ----------------------------------------
            # LOGIN MAY HAVE COMPLETED
            # ----------------------------------------

            # Give Instagram time to establish the
            # authenticated session after CAPTCHA.
            page.wait_for_timeout(3000)

            # Look for normal Instagram page content.
            links = page.locator("a[href]")

            if links.count() > 0:

                print(
                    "Login and verification completed."
                )

                # Give Instagram additional time to
                # finish rendering the authenticated UI.
                page.wait_for_timeout(2000)

                return True

        except Exception:
            pass

        page.wait_for_timeout(1000)

    raise RuntimeError(
        "Instagram login/verification timed out.\n"
        "Please restart MootCheck and try again."
    )


def get_logged_in_username(page):
    """Determine the username of the logged-in Instagram account."""

    print("Detecting logged-in account...")

    ignored = {
        "accounts",
        "explore",
        "direct",
        "reels",
        "stories",
        "about",
        "developer",
        "privacy",
        "terms",
    }

    # Give Instagram a little time to finish rendering
    # the authenticated navigation/profile elements.
    deadline = time.time() + 20

    while time.time() < deadline:

        try:

            links = page.locator("a[href]")

            for i in range(links.count()):

                try:

                    href = links.nth(i).get_attribute("href")

                    if not href:
                        continue

                    match = re.fullmatch(
                        r"/([A-Za-z0-9._]+)/?",
                        href
                    )

                    if not match:
                        continue

                    username = match.group(1)

                    if username.lower() in ignored:
                        continue

                    # Ignore obvious non-profile routes.
                    if username.lower() in {
                        "login",
                        "signup",
                        "emails",
                        "settings",
                    }:
                        continue

                    print(
                        f"Logged in as @{username}"
                    )

                    return username

                except Exception:
                    pass

        except Exception:
            pass

        page.wait_for_timeout(1000)

    raise RuntimeError(
        "Could not automatically detect the "
        "logged-in Instagram username.\n\n"
        "Make sure Instagram has completely finished "
        "the login and verification process, then try again."
    )


def get_chromium_path():
    """
    Find Chromium whether running normally
    from Python or from a PyInstaller EXE.
    """

    if getattr(sys, "frozen", False):

        # ----------------------------------------
        # Running as PyInstaller EXE
        # ----------------------------------------

        base_dir = sys._MEIPASS

        chromium_path = os.path.join(
            base_dir,
            "chromium",
            "chrome-win64",
            "chrome.exe"
        )

    else:

        # ----------------------------------------
        # Running normally from Python
        # ----------------------------------------

        chromium_path = os.path.join(
            os.environ["LOCALAPPDATA"],
            "ms-playwright",
            "chromium-1234",
            "chrome-win64",
            "chrome.exe"
        )

    if not os.path.isfile(chromium_path):

        raise FileNotFoundError(
            "MootCheck could not find Chromium.\n\n"
            f"Expected location:\n{chromium_path}"
        )

    return chromium_path


def run_mootcheck():
    """
    Main MootCheck function.

    Returns:
        {
            "followers": set,
            "following": set,
            "mutuals": set,
            "not_following_back": set,
            "followers_you_dont_follow": set
        }
    """

    print("\n========================================")
    print("             MOOTCHECK")
    print("========================================")

    with sync_playwright() as p:

        # ----------------------------------------
        # FIND CHROMIUM
        # ----------------------------------------

        chromium_path = get_chromium_path()

        print(
            f"\nUsing Chromium:\n"
            f"{chromium_path}"
        )

        # ----------------------------------------
        # START BROWSER
        # ----------------------------------------

        browser = p.chromium.launch(
            executable_path=chromium_path,
            headless=False
        )

        # ----------------------------------------
        # CREATE CONTEXT
        # ----------------------------------------

        context = browser.new_context()

        page = context.new_page()

        try:

            # ----------------------------------------
            # LOGIN
            # ----------------------------------------

            wait_for_login(page)

            # ----------------------------------------
            # DETECT ACCOUNT
            # ----------------------------------------

            username = get_logged_in_username(page)

            # ----------------------------------------
            # OPEN PROFILE
            # ----------------------------------------

            print(
                f"\nOpening profile "
                f"@{username}..."
            )

            page.goto(
                f"https://www.instagram.com/{username}/",
                wait_until="domcontentloaded",
                timeout=30000
            )

            page.wait_for_timeout(3000)

            # ----------------------------------------
            # FOLLOWERS
            # ----------------------------------------

            followers = collect_users(
                page,
                "followers"
            )

            # ----------------------------------------
            # FOLLOWING
            # ----------------------------------------

            following = collect_users(
                page,
                "following"
            )

            # ----------------------------------------
            # COMPARE
            # ----------------------------------------

            mutuals = followers & following

            not_following_back = (
                following - followers
            )

            followers_you_dont_follow = (
                followers - following
            )

            return {
                "followers": followers,
                "following": following,
                "mutuals": mutuals,
                "not_following_back":
                    not_following_back,
                "followers_you_dont_follow":
                    followers_you_dont_follow,
            }

        finally:

            # Close browser when finished.
            browser.close()


if __name__ == "__main__":

    try:

        results = run_mootcheck()

        print("\n========================================")
        print("              RESULTS")
        print("========================================")

        print(
            "Followers:",
            len(results["followers"])
        )

        print(
            "Following:",
            len(results["following"])
        )

        print(
            "Mutuals:",
            len(results["mutuals"])
        )

        print(
            "Don't follow you back:",
            len(results["not_following_back"])
        )

        print(
            "You don't follow back:",
            len(results["followers_you_dont_follow"])
        )

    except Exception as e:

        print("\n========================================")
        print("               ERROR")
        print("========================================")

        print(e)