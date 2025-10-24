import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor
import threading

output_dir = "output"
visited_urls = set()
lock = threading.Lock()
max_depth = 3
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
session = requests.Session()
session.headers.update({'User-Agent': user_agent})

def create_output_dir():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

def save_file(url, content, extension=None, website_name=None):
    parsed_url = urlparse(url)
    path = parsed_url.path
    if not path:
        path = 'index.html'
    filename = os.path.basename(path)
    if extension and not filename.endswith(extension):
        filename += extension
    if website_name:
        website_dir = os.path.join(output_dir, website_name)
        if not os.path.exists(website_dir):
            os.makedirs(website_dir)
        filepath = os.path.join(website_dir, filename)
    else:
        filepath = os.path.join(output_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(content)

def check_robots_txt(url):
    robots_url = urljoin(url, '/robots.txt')
    try:
        response = session.get(robots_url, timeout=5)
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

def grab_webserver(url, base_url=None, depth=0):
    if depth > max_depth:
        return
    if url in visited_urls:
        return
    with lock:
        visited_urls.add(url)

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()

        parsed_url = urlparse(url)
        path = parsed_url.path
        if not path:
            path = 'index.html'
        extension = os.path.splitext(path)[1]
        if not extension:
            extension = '.html'

        if base_url:
            base_parsed = urlparse(base_url)
            website_name = base_parsed.netloc
            if website_name.startswith('www.'):
                website_name = website_name[4:]
        else:
            website_name = None

        save_file(url, response.content, extension, website_name)

        if extension == '.html':
            soup = BeautifulSoup(response.content, 'html.parser')

            with ThreadPoolExecutor(max_workers=10) as executor:
                for link in soup.find_all(['a', 'link', 'script', 'img']):
                    if link.name == 'a':
                        href = link.get('href')
                        if href:
                            absolute_url = urljoin(url, href)
                            if absolute_url not in visited_urls:
                                executor.submit(grab_webserver, absolute_url, base_url, depth+1)
                    elif link.name == 'link':
                        href = link.get('href')
                        if href and 'stylesheet' in link.get('rel', []):
                            absolute_url = urljoin(url, href)
                            if absolute_url not in visited_urls:
                                executor.submit(grab_webserver, absolute_url, base_url, depth+1)
                    elif link.name == 'script':
                        src = link.get('src')
                        if src:
                            absolute_url = urljoin(url, src)
                            if absolute_url not in visited_urls:
                                executor.submit(grab_webserver, absolute_url, base_url, depth+1)
                    elif link.name == 'img':
                        src = link.get('src')
                        if src:
                            absolute_url = urljoin(url, src)
                            if absolute_url not in visited_urls:
                                executor.submit(grab_webserver, absolute_url, base_url, depth+1)

    except requests.exceptions.RequestException as e:
        print(f"Failed to grab {url}: {e}")

def main():
    create_output_dir()
    base_url = input("Enter the URL of the webserver to grab: ")
    robots_txt = check_robots_txt(base_url)
    if robots_txt and 'Disallow: /' in robots_txt:
        print("This website has requested not to be crawled. Exiting.")
        return
    grab_webserver(base_url, base_url)
    print("Webserver grabbing completed. Files saved in the 'output/websitename' directory.")

if __name__ == "__main__":
    main()
