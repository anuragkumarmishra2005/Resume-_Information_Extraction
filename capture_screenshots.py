"""Playwright screenshot capture script for Streamlit GUI verification."""

import os
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def capture():
    print("Launching Playwright Chromium...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        print("Navigating to Streamlit app at http://localhost:8501...")
        page.goto("http://localhost:8501", timeout=30000)
        page.wait_for_selector(".main-header", timeout=15000)
        time.sleep(2)

        # Select sample resume from selectbox
        print("Selecting 'Anurag Mishra (Real PDF)' sample...")
        # In streamlit, click on the selectbox
        selectbox = page.locator('div[data-baseweb="select"]')
        if selectbox.count() > 0:
            selectbox.click()
            time.sleep(1)
            # Find the option with Anurag Mishra
            option = page.locator('li:has-text("Anurag Mishra (Real PDF)")')
            if option.count() > 0:
                option.click()
                time.sleep(1)

        # Click the Extract Information button
        print("Clicking Extract Information button...")
        extract_btn = page.locator('button:has-text("Extract Information")')
        extract_btn.click()

        # Wait for processing to complete (check for Candidate Name metric or success alert)
        print("Waiting for extraction to finish...")
        page.wait_for_selector('div[data-testid="stMetricValue"]:has-text("Anurag Kumar Mishra")', timeout=20000)
        time.sleep(2)

        # 1. Capture Overview Screen (Full Page)
        overview_path = os.path.join(SCREENSHOTS_DIR, "gui_overview.png")
        page.screenshot(path=overview_path, full_page=True)
        print(f"Captured: {overview_path}")

        # 2. Click Skills Tab and scroll down to content
        print("Switching to Skills tab...")
        skills_tab = page.locator('button[data-baseweb="tab"]:has-text("Skills")')
        if skills_tab.count() > 0:
            skills_tab.click()
            time.sleep(1)
        skills_path = os.path.join(SCREENSHOTS_DIR, "gui_skills_experience.png")
        page.screenshot(path=skills_path, full_page=True)
        print(f"Captured: {skills_path}")

        # 3. Switch to Experience Tab
        print("Switching to Experience tab...")
        exp_tab = page.locator('button[data-baseweb="tab"]:has-text("Experience")')
        if exp_tab.count() > 0:
            exp_tab.click()
            time.sleep(1)
        downloads_path = os.path.join(SCREENSHOTS_DIR, "gui_downloads.png")
        page.screenshot(path=downloads_path, full_page=True)
        print(f"Captured: {downloads_path}")

        browser.close()
        print("All screenshots successfully captured!")


if __name__ == "__main__":
    capture()
