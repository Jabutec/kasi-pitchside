import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


class PSLWebsiteClient:
    def __init__(self, base_url: str = "https://www.psl.co.za"):
        self.target_url = f"{base_url.rstrip('/')}/matchcentre?type=fixtures"

    def get_fixtures(self) -> List[Dict[str, str]]:
        fixtures: List[Dict[str, str]] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            print(f"[PSL Ingestion] Fetching matchcentre data...")
            page.goto(self.target_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)

            # FIX: the site paginates fixtures 8 rows at a time via a
            # click-triggered loadmore() JS function (confirmed by reading
            # matchcentre.js directly) — NOT via scroll. Scrolling never
            # revealed more rows because nothing binds loadmore() to a
            # scroll event. Call the function directly and keep calling
            # it until the row count stops growing.
            print("[PSL Ingestion] Triggering loadmore() until all fixtures are loaded...")

            def count_fixture_rows() -> int:
                # table-standings-fixtures > tbody is the container
                # loadmore() operates on, per matchcentre.js
                return page.evaluate(
                    "document.querySelectorAll('#table-standings-fixtures > tbody').length"
                )

            previous_count = -1
            current_count = count_fixture_rows()
            max_clicks = 50  # safety ceiling, a full season is nowhere near this many loadmore() calls
            clicks = 0

            while current_count != previous_count and clicks < max_clicks:
                previous_count = current_count
                try:
                    page.evaluate("loadmore()")
                except Exception as e:
                    print(f"[PSL Ingestion] loadmore() call failed or button gone: {e}")
                    break
                page.wait_for_timeout(600)  # let the DOM update
                current_count = count_fixture_rows()
                clicks += 1
                print(f"[PSL Ingestion]   click {clicks}: {current_count} row groups loaded")

            print(f"[PSL Ingestion] Stopped after {clicks} loadmore() calls, "
                  f"{current_count} row groups total (stable count, no more new rows).")

            html_content = page.content()
            browser.close()

        soup = BeautifulSoup(html_content, "html.parser")

        vs_nodes = soup.find_all(text=lambda t: t and ("VS" in t or "vs" in t or "-" in t))
        seen_keys = set()

        for vs in vs_nodes:
            parent = vs.parent
            for _ in range(4):
                if not parent:
                    break
                text_lines = [line.strip() for line in parent.get_text("\n").split("\n") if line.strip()]

                date_line = next((line for line in text_lines if re.search(r"\d{2}\s+[A-Za-z]{3}", line)), None)

                if date_line and len(text_lines) >= 3:
                    cleaned_lines = [t for t in text_lines if t not in ["FIXTURES", "RESULTS", "LIVE", "VS"]]

                    if len(cleaned_lines) >= 3:
                        home_team = cleaned_lines[0]
                        score = None
                        status = "UPCOMING"

                        # FIX: a completed match row has an extra line —
                        # the score — sitting BETWEEN the two team names:
                        #   upcoming: [home_team, away_team, date_line]
                        #   completed: [home_team, score, away_team, date_line]
                        # My earlier version discarded these rows entirely,
                        # wrongly assuming the real away_team was lost. It
                        # wasn't lost — it's one position further along.
                        # Detect the shape and shift the index instead of
                        # dropping real match data.
                        score_pattern = re.match(r'^(\d+)\s*-\s*(\d+)$', cleaned_lines[1].strip())
                        if score_pattern and len(cleaned_lines) >= 4:
                            score = cleaned_lines[1].strip()
                            away_team = cleaned_lines[2]
                            status = "COMPLETED"
                        else:
                            away_team = cleaned_lines[1]

                        date_match = re.search(r"(\d{2}\s+[A-Za-z]{3})", date_line)
                        time_match = re.search(r"(\d{2}:\d{2})", date_line)
                        venue_split = date_line.split("-")

                        date_str = date_match.group(1) if date_match else "N/A"
                        time_str = time_match.group(1) if time_match else "N/A"
                        venue_str = venue_split[1].strip() if len(venue_split) > 1 else "N/A"

                        # Genuine junk (site nav/title text, not a real
                        # match row) never resolves to a real venue or
                        # has home_team == away_team — safe to drop.
                        if venue_str == "N/A" or home_team == away_team:
                            break

                        uniq_key = f"{date_str}_{home_team}_{away_team}"
                        if uniq_key not in seen_keys:
                            seen_keys.add(uniq_key)
                            fixtures.append({
                                "date": date_str,
                                "home_team": home_team,
                                "away_team": away_team,
                                "score": score,
                                "time": time_str,
                                "venue": venue_str,
                                "status": status
                            })
                    break
                parent = parent.parent

        return fixtures


if __name__ == "__main__":
    client = PSLWebsiteClient()

    print("--- Extracting Current Fixtures ---")
    fixtures = client.get_fixtures()
    print(f"Extracted {len(fixtures)} matches.\n")

    out_file = Path("data/current_season_matches.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2)

    print(f"[PSL Ingestion] Saved output to {out_file}")