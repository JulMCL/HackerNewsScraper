import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup

headers = {"User-Agent": "my-learning-scraper/1.0"}
base_url = "https://news.ycombinator.com/news"
max_pages = 5

data_dir = Path("data")
raw_dir = data_dir / "raw"
processed_dir = data_dir / "processed"

response = requests.get(base_url, headers=headers, timeout=20)

def parse_page(html, page_num):
    soup = BeautifulSoup(html, "html.parser")
    page_posts = []

    for row in soup.find_all("tr", class_="athing"):
        # extract the title and URL from the current row
        title_element = row.find('span', class_='titleline').a

        # obtain the metadata row that immediately follows this row
        subtext_row = row.find_next_sibling('tr')
        if subtext_row is None:
            continue  # skip malformed rows instead of crashing

        # extract points, author, rank, and comments from the subtext row
        score_elem = subtext_row.find('span', class_='score')
        score = score_elem.text if score_elem else '0 points'

        author_elem = subtext_row.find('a', class_='hnuser')
        author = author_elem.text if author_elem else 'Unknown'

        rank_elem = row.find('span', class_='rank')
        rank = rank_elem.get_text(strip=True).rstrip('.') if rank_elem else '0'

        subtext_td = subtext_row.find('td', class_='subtext')
        comment_links = subtext_td.find_all('a') if subtext_td else []
        comments = '0 comments'

        for a in comment_links:
            if 'comment' in a.text or 'discuss' in a.text:
                comments = a.text.replace('\xa0', ' ')
                break

        page_posts.append({
            "title": title_element.text,
            "url": title_element["href"],
            "points": score,
            "author": author,
            "rank": int(rank),
            "comments": comments,
            "page": page_num,
        })

    return page_posts

def fetch_page(page_num):
    try:
        response = requests.get(f"{base_url}?p={page_num}", headers=headers, timeout=10)
    
    except requests.RequestException as e:
        print(f"Page {page_num}: got {response.status_code}, stopping.")
        return None

    if response.status_code != 200:
        print(f"Page {page_num}: got {response.status_code}, stopping this run.")
        return None
    
    return response.text

def save_raw(html, run_id, page_num):
    folder = raw_dir / run_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"page_{page_num}.html").write_text(html, encoding="utf-8")

def run():
    now = datetime.now()
    run_id = now.strftime("%Y-%m-%d at %H:%M")

    master_posts = []
    for page in range(1, max_pages + 1):
        html = fetch_page(page)
        if html is None:
            break
        save_raw(html, run_id, page)
        master_posts.extend(parse_page(html, page))
        time.sleep(4)

    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / f"hn_{run_id}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"Collected at (UTC): {now}\n")
        f.write(f"Posts: {len(master_posts)}\n\n")
        for post in master_posts:
            f.write(f"Title: {post['title']}\n")
            f.write(f"URL: {post['url']}\n")
            f.write(f"Points: {post['points']}\n")
            f.write(f"Author: {post['author']}\n")
            f.write(f"Rank: {post['rank']}\n")
            f.write(f"Comments: {post['comments']}\n")
            f.write(f"Page: {post['page']}\n")
            f.write("-" * 40 + "\n")

    print(f"{run_id}: saved {len(master_posts)} posts to {out_path}")

if __name__ == "__main__":
    run()