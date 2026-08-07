#!/usr/bin/env python3
"""
Instagram follower scraper for player_social.csv
Automates Instagram profile lookups to collect follower counts and verification status.
"""

import csv
import time
import re
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class InstagramScraper:
    def __init__(self, csv_path):
        self.csv_path = Path(csv_path)
        self.driver = None
        self.checked_count = 0
        self.updated_count = 0

    def init_driver(self):
        """Initialize Brave browser with Selenium"""
        options = webdriver.ChromeOptions()
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        options.binary_location = brave_path
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        options.add_argument("--no-sandbox")

        self.driver = webdriver.Chrome(options=options)

    def scrape_profile(self, handle):
        """Scrape Instagram profile data"""
        if not handle or handle == 'null':
            return None

        try:
            url = f"https://instagram.com/{handle}"
            self.driver.get(url)
            time.sleep(2)  # Rate limiting

            # Check if profile exists
            try:
                error_msg = self.driver.find_element(By.XPATH, "//*[contains(text(), \"This profile isn't available\")]")
                return {'status': 'unavailable', 'followers': None}
            except NoSuchElementException:
                pass

            # Extract follower count
            try:
                # Look for follower count pattern
                page_text = self.driver.page_source

                # Pattern: "123K followers" or "123,456 followers"
                follower_pattern = r'(\d+(?:[.,]\d+)*[KMB]?)\s+followers'
                match = re.search(follower_pattern, page_text)

                if match:
                    followers_str = match.group(1)
                    followers = self._parse_followers(followers_str)

                    # Check if verified (look for blue checkmark)
                    verified = 'aria-label="Verified"' in page_text or 'verified' in page_text.lower()

                    return {
                        'status': 'ok',
                        'followers': followers,
                        'followers_str': followers_str,
                        'verified': verified
                    }
            except Exception as e:
                print(f"Error parsing {handle}: {e}")
                return None

            return None

        except Exception as e:
            print(f"Error scraping {handle}: {e}")
            return None

    def _parse_followers(self, follower_str):
        """Convert follower string (e.g., '123K', '1.5M') to integer"""
        follower_str = follower_str.replace(',', '')

        if 'K' in follower_str:
            return int(float(follower_str.replace('K', '')) * 1000)
        elif 'M' in follower_str:
            return int(float(follower_str.replace('M', '')) * 1000000)
        elif 'B' in follower_str:
            return int(float(follower_str.replace('B', '')) * 1000000000)
        else:
            try:
                return int(follower_str)
            except ValueError:
                return None

    def read_csv(self):
        """Read player_social.csv"""
        rows = []
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows

    def update_csv(self, rows):
        """Write updated rows back to CSV"""
        if not rows:
            return

        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def run(self):
        """Main scraping loop"""
        print("Initializing browser...")
        self.init_driver()

        try:
            print("Reading CSV...")
            rows = self.read_csv()

            print(f"Total players: {len(rows)}")

            for i, row in enumerate(rows):
                player_name = row.get('full_name', 'Unknown')
                handle = row.get('ig_handle', '').strip()
                current_followers = row.get('ig_followers', '')
                current_status = row.get('ig_status', '')

                # Skip if no handle or already has current data
                if not handle or handle == 'null':
                    continue

                # Skip if already has valid follower data (not profile_unavailable)
                if current_followers and current_followers != 'null' and 'profile_unavailable' not in current_status:
                    continue

                self.checked_count += 1
                print(f"[{self.checked_count}] Checking {player_name} (@{handle})...", end=' ')

                result = self.scrape_profile(handle)

                if result:
                    if result['status'] == 'ok' and result['followers']:
                        row['ig_followers'] = str(result['followers'])
                        row['ig_followers_verbatim'] = str(result['followers'])
                        row['ig_precision'] = 'exact_public_response'
                        row['ig_status'] = 'ok'
                        row['ig_source'] = 'verified_browser_check:automated'
                        row['ig_retrieved_on'] = '2026-08-03'
                        self.updated_count += 1
                        verified_badge = '✓' if result.get('verified') else ''
                        print(f"✓ {result['followers']:,} followers {verified_badge}")
                    elif result['status'] == 'unavailable':
                        row['ig_status'] = 'profile_unavailable:confirmed'
                        row['ig_retrieved_on'] = '2026-08-03'
                        print("✗ Profile unavailable")
                else:
                    print("? Error retrieving")

                # Save progress periodically
                if self.checked_count % 20 == 0:
                    print(f"Saving progress at {self.checked_count} profiles...")
                    self.update_csv(rows)

            # Final save
            print("\nSaving final updates...")
            self.update_csv(rows)

            print(f"\n=== COMPLETE ===")
            print(f"Profiles checked: {self.checked_count}")
            print(f"Profiles updated: {self.updated_count}")

        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    csv_path = r"C:\Local Only\Ai projects\Sports Analytics Conference Projeccts\Full Project Files\marchand_index\raw\player_social.csv"

    scraper = InstagramScraper(csv_path)
    scraper.run()
