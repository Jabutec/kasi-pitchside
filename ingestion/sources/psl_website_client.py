import json
import re
from pathlib import Path
from typing import Dict, List
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


class PSLWebsiteClient:
    def __init__(self, base_url: str = "https://www.psl.co.za"):
        self.target_url = f"{base_url.rstrip('/')}/matchcentre?type=fixtures"

    def get_fixtures(self) -> List[Dict[str, str]]:
        fixtures: List[Dict[str, str]] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.set_extra_http_headers({
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            })

            print(f"[PSL Ingestion] Navigating to {self.target_url}...")
            page.goto(self.target_url, wait_until="networkidle", timeout=45000)

            # Auto-scroll iteratively to force loading all lazy-loaded fixtures
            print("[PSL Ingestion] Scrolling to load full fixture list...")
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 3000)")
                page.wait_for_timeout(1000)

            html_content = page.content()
            browser.close()

        soup = BeautifulSoup(html_content, "html.parser")
        
        # Locate individual match containers or fall back to resilient string splits
        full_text = soup.get_text()

        # Permissive regex capturing variations in team names, dates, and times
        pattern = re.compile(
            r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s*([^\n\r]+?)\s*VS\s*([^\n\r]+?)\s*(\d{1,2}\s+[A-Za-z]{3}\s+\d{2}:\d{2}|\d{2}:\d{2})\s*-\s*([^\n\r]+)",
            re.IGNORECASE
        )

        matches = pattern.findall(full_text)
        seen_keys = set()

        for date_str, home, away, time_str, venue in matches:
            clean_home = home.strip()
            clean_away = away.strip()
            clean_date = date_str.strip()

            # Clean time string to retain only HH:MM format
            clean_time = time_str.strip()
            if len(clean_time.split()) > 1:
                clean_time = clean_time.split()[-1]

            uniq_key = f"{clean_date}_{clean_home}_{clean_away}"
            if uniq_key not in seen_keys:
                seen_keys.add(uniq_key)
                fixtures.append({
                    "date": clean_date,
                    "home_team": clean_home,
                    "away_team": clean_away,
                    "time": clean_time,
                    "venue": venue.strip(),
                    "status": "UPCOMING"
                })

        return fixtures


if __name__ == "__main__":
    client = PSLWebsiteClient()
    all_fixtures = client.get_fixtures()

    print(f"\n[PSL Ingestion] Extracted {len(all_fixtures)} total fixtures.")

    output_path = Path("data/raw_fixtures.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_fixtures, f, indent=2)

    print(f"[PSL Ingestion] Fixtures successfully saved to {output_path}")