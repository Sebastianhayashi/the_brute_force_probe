import os
import subprocess
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import re

# 设置分支和克隆目录
branch = 'jazzy'
clone_base_dir = './'
max_threads = 32  # 根据你的机器调整并行线程数

def fetch_sitemap(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Failed to fetch sitemap from {url}: {e}")
        return None

def get_ros_package_urls(sitemap):
    soup = BeautifulSoup(sitemap, 'xml')
    ros_package_urls = []
    for loc_tag in soup.find_all('loc'):
        url = loc_tag.text.strip()
        if '/repos/' in url:  # 检查是否为 ROS 包 URL
            ros_package_urls.append(url)
    return ros_package_urls

def map_checkout_url(checkout_url):
    """
    Map the extracted checkout_url to the actual GitHub repository URL.
    Handles different patterns.
    """
    if checkout_url.startswith('https://github.com'):
        return checkout_url
    elif checkout_url.startswith('/r/'):
        # 示例: /r/abb/github-ros-industrial-abb
        # 期望映射到 https://github.com/ros-industrial/abb.git
        match = re.match(r'^/r/(?P<repo_name>[^/]+)/github-ros-industrial-[^/]+$', checkout_url)
        if match:
            repo_name = match.group('repo_name')
            return f"https://github.com/ros-industrial/{repo_name}.git"
        else:
            print(f"Unexpected checkout URL format: {checkout_url}")
            return None
    else:
        print(f"Unknown checkout URL format: {checkout_url}")
        return None

def get_checkout_url(package_url):
    try:
        response = requests.get(package_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 查找包含 'github.com' 的链接
        checkout_uri_tag = soup.find('a', href=lambda x: x and 'github.com' in x)

        if checkout_uri_tag:
            checkout_url = checkout_uri_tag['href']
            print(f"[DEBUG] Found checkout_url: {checkout_url}")  # 调试信息

            # 如果 URL 是相对路径，拼接成完整的 URL
            if not checkout_url.startswith('http'):
                checkout_url = urljoin(package_url, checkout_url)
                print(f"[DEBUG] Converted to absolute URL: {checkout_url}")  # 调试信息

            # 处理特定的 GitHub URL 格式
            repo_url = map_checkout_url(checkout_url)
            print(f"[DEBUG] Mapped repo_url: {repo_url}")  # 调试信息

            return repo_url
        else:
            print(f"No checkout URL found for {package_url}")
            return None
    except requests.RequestException as e:
        print(f"Exception occurred while fetching checkout URL for {package_url}: {e}")
        return None

def clone_repository(repo_url, branch='jazzy'):
    if repo_url:
        # 从 repo_url 中提取包名
        package_name = repo_url.rstrip('.git').split('/')[-1]

        # 检查是否已经克隆该包
        if os.path.exists(os.path.join(clone_base_dir, package_name)):
            print(f"Package '{package_name}' already exists. Skipping.")
            return

        # 执行 git clone 操作
        try:
            print(f"Cloning '{repo_url}' into '{package_name}'...")
            subprocess.run(['git', 'clone', repo_url, '-b', branch], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error while cloning '{repo_url}': {e}")
            # 尝试克隆默认分支
            try:
                print(f"Falling back to default branch for '{repo_url}'...")
                subprocess.run(['git', 'clone', repo_url], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone '{repo_url}': {e}")

def process_package(package_url):
    print(f"Processing package: {package_url}")
    checkout_url = get_checkout_url(package_url)
    if checkout_url:
        clone_repository(checkout_url, branch)
    else:
        print(f"No valid checkout URL found for {package_url}. Skipping.")

def main():
    sitemap_url = 'https://index.ros.org/sitemap.xml'
    sitemap = fetch_sitemap(sitemap_url)
    if sitemap:
        ros_package_urls = get_ros_package_urls(sitemap)
        print(f"Found {len(ros_package_urls)} ROS package URLs.")

        # 使用线程池来并行处理每个包
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(process_package, package_url) for package_url in ros_package_urls]

            # 等待任务完成
            for future in as_completed(futures):
                try:
                    future.result()  # 触发异常（如果有的话）
                except Exception as e:
                    print(f"Error in processing package: {e}")

if __name__ == "__main__":
    main()