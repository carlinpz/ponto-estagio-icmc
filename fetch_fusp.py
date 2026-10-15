import urllib.request
import re
from bs4 import BeautifulSoup

url = 'https://www.fusp.org.br/boletim-de-frequ%C3%AAncia'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
html = urllib.request.urlopen(req).read().decode('utf-8', 'ignore')

soup = BeautifulSoup(html, 'html.parser')

print("Page Title:", soup.title.string if soup.title else "No title")

# Find main content
main = soup.find('main') or soup.find('div', class_='content') or soup.body
if main:
    print("\n--- TEXT SNIPPETS ---")
    for p in main.find_all(['h1', 'h2', 'h3', 'p', 'a']):
        text = p.get_text(strip=True)
        href = p.get('href')
        if text or href:
            if href:
                print(f"[{p.name}] {text} -> {href}")
            else:
                print(f"[{p.name}] {text}")
