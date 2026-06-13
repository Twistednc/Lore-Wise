import requests
from bs4 import BeautifulSoup

_HEADERS = {"User-Agent": "LoreWise/1.0"}

def fetch_fandom(wiki_host: str, query: str) -> str:
    if not wiki_host: return "No wiki host provided."
    
    base = f"https://{wiki_host}/api.php"
    try:
        # 1. Search
        r = requests.get(base, params={"action": "opensearch", "search": query, "limit": 1, "format": "json"}, timeout=5)
        r.raise_for_status()
        data = r.json()
        
        if len(data) < 2 or not data[1]:
            return f"No results found for '{query}'."
        
        title = data[1][0]

        # 2. Parse
        r = requests.get(base, params={"action": "parse", "page": title, "prop": "text", "format": "json", "redirects": 1}, timeout=5)
        r.raise_for_status()
        parse_data = r.json().get("parse")
        
        if not parse_data:
            return "Could not parse page data."
            
        html = parse_data.get("text", {}).get("*", "")
        soup = BeautifulSoup(html, "html.parser")
        
        # Cleanup
        for tag in soup(["table", "script", "style", "aside", "figure", "noscript"]):
            tag.decompose()
        for edit in soup.select(".mw-editsection, .toc, .navbox, .infobox, .reference"):
            edit.decompose()

        # URLs
        for a in soup.find_all('a', href=True):
            if a['href'].startswith('/wiki/'):
                a['href'] = f"https://{wiki_host}{a['href']}"
        
        for img in soup.find_all('img', src=True):
            if img['src'].startswith('/'):
                img['src'] = f"https://{wiki_host}{img['src']}"
            img['width'] = "100%" # Force images to scale to panel

        content = ""
        # Get headers, paragraphs, lists, and images
        for element in soup.find_all(['p', 'ul', 'ol', 'h2', 'img']):
            content += str(element)
            if len(content) > 8000: break 

        if not content.strip():
            return "The page was found but no readable content could be extracted."

        return f"<h2>{title}</h2>{content}"
        
    except Exception as e:
        return f"Error fetching from wiki: {str(e)}"

def search(wiki_base: str, game_name: str, query: str) -> str:
    # Use DuckDuckGo as a backup if wiki_base is empty or fails
    if wiki_base:
        return fetch_fandom(wiki_base, query)
    return f"Search for '{query}' - (No official wiki linked in games.json)"