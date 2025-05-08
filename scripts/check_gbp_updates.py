"""
Verifică paginile oficiale Google Business Profile și trimite alertă Slack
dacă data „Last updated” este mai nouă decât cea din docs_links.md.
"""

import os, re, datetime as dt, requests
from pathlib import Path
from bs4 import BeautifulSoup
from slack_sdk import WebClient

# --- CONFIG ---------------------------------
DOCS = {
    "Performance API": "https://developers.google.com/my-business/reference/performance/rest",
    "Policies":        "https://developers.google.com/my-business/content/policies",
    "Review Data":     "https://developers.google.com/my-business/content/review-data",
}
TABLE_FILE     = Path("docs_links.md")
DATE_STR_REGEX = r"Last updated (\w+ \d{1,2}, \d{4})"
OUT_FMT        = "%Y-%m-%d"
SLACK_TOKEN    = os.getenv("SLACK_TOKEN")
SLACK_CHANNEL  = os.getenv("SLACK_CHANNEL", "#alerts")

# --- FUNCTIONS ------------------------------
def fetch_last_updated(url: str) -> dt.date | None:
    html = requests.get(url, timeout=15).text
    m = re.search(DATE_STR_REGEX, html)
    if not m:
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.select_one(".devsite-article-last-updated")
        if tag:
            m = re.search(DATE_STR_REGEX, tag.text)
    if m:
        return dt.datetime.strptime(m.group(1), "%B %d, %Y").date()
    return None

def load_table_dates() -> dict[str, dt.date]:
    dates = {}
    for line in TABLE_FILE.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Performance") or line.startswith("| Review") or line.startswith("| Content"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            name, date_txt = parts[0], parts[-1]
            try:
                dates[name] = dt.datetime.strptime(date_txt, OUT_FMT).date()
            except ValueError:
                pass
    return dates

def alert_slack(name: str, url: str, new_date: dt.date) -> None:
    if not SLACK_TOKEN:
        print(f"[INFO] {name} actualizat {new_date}")
        return
    WebClient(token=SLACK_TOKEN).chat_postMessage(
        channel=SLACK_CHANNEL,
        text=f"🔔 *GBP docs update* → *{name}* ({new_date:%Y-%m-%d})\n<{url}>"
    )

# --- MAIN -----------------------------------
def main() -> int:
    saved = load_table_dates()
    for name, url in DOCS.items():
        latest = fetch_last_updated(url)
        if latest and (name not in saved or latest > saved[name]):
            alert_slack(name, url, latest)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
