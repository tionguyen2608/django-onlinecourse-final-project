import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "screenshots"


def capture():
    OUTPUT.mkdir(exist_ok=True)
    subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "manage.py", "seed_demo"], cwd=ROOT, check=True)
    password = os.environ.get("DEMO_ADMIN_PASSWORD") or (ROOT / ".local-demo-password").read_text().strip()
    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    try:
        for attempt in range(30):
            if server.poll() is not None:
                raise RuntimeError("The Django development server stopped unexpectedly.")
            try:
                with urlopen("http://127.0.0.1:8000/onlinecourse/", timeout=1) as response:
                    if response.status == 200:
                        break
            except (URLError, TimeoutError):
                time.sleep(0.5)
        else:
            raise RuntimeError("The Django development server did not become ready.")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="light")
            page = context.new_page()
            page.goto("http://127.0.0.1:8000/admin/")
            page.get_by_label("Username:", exact=True).fill("datadmin")
            page.get_by_label("Password:", exact=True).fill(password)
            page.get_by_role("button", name="Log in", exact=True).click()
            page.get_by_role("heading", name="Site administration", exact=True).wait_for()
            assert page.get_by_role("link", name="Authentication and Authorization", exact=True).is_visible()
            assert page.get_by_role("link", name="OnlineCourse", exact=True).is_visible()
            page.screenshot(path=str(OUTPUT / "03-admin-site.png"), full_page=True)
            page.goto("http://127.0.0.1:8000/onlinecourse/")
            course_link = page.get_by_role("link", name="View course", exact=True)
            if not course_link.count():
                course_link = page.get_by_role("link", name="Continue learning", exact=True)
            course_link.click()
            enroll = page.get_by_role("button", name="Enroll to take the exam", exact=True)
            if enroll.count():
                enroll.click()
            page.get_by_role("button", name="Submit exam", exact=True).wait_for()
            page.screenshot(path=str(OUTPUT / "04-course-details.png"), full_page=True)
            for answer in ["Python objects and database tables", "A QuerySet of matching records", "ForeignKey", "ManyToManyField"]:
                page.get_by_label(answer, exact=True).check()
            page.get_by_role("button", name="Submit exam", exact=True).click()
            page.get_by_role("heading", name="Congratulations, Dat!", exact=True).wait_for()
            assert page.get_by_text("Score: 100%", exact=True).is_visible()
            assert page.get_by_role("heading", name="Exam results", exact=True).is_visible()
            page.screenshot(path=str(OUTPUT / "07-final.png"), full_page=True)
            browser.close()
        print("Saved 03-admin-site.png, 04-course-details.png and 07-final.png from the running application.")
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


if __name__ == "__main__":
    capture()
