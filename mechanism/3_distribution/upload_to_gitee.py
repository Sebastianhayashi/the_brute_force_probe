#!/usr/bin/env python3

import os
import re
import shutil
import requests
import sys
from urllib.parse import urljoin

# 配置部分
SPECS_DIR = os.path.expanduser('~/SPECS')
SOURCES_DIR = os.path.expanduser('~/SOURCES')
OUTPUT_DIR = os.path.expanduser('~/gitee_repos')  # 存放所有仓库的目录

# 从环境变量中获取 Gitee 个人访问令牌
GITEE_TOKEN = os.getenv('GITEE_TOKEN')
if not GITEE_TOKEN:
    print("错误: 请在环境变量 GITEE_TOKEN 中设置您的 Gitee 个人访问令牌。")
    sys.exit(1)

# Gitee 用户名或组织名（可选，如果需要在特定组织下创建仓库）
GITEE_ORG = os.getenv('GITEE_ORG')  # 如果不在组织下创建，保持为空

# Gitee API 基础 URL
GITEE_API_BASE = "https://gitee.com/api/v5/"

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_spec_info(spec_path):
    """
    从 .spec 文件中提取包名、版本和依赖项
    """
    name = None
    version = None
    requires = []
    build_requires = []

    with open(spec_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('Name:'):
                name = line.split(':', 1)[1].strip()
            elif line.startswith('Version:'):
                version = line.split(':', 1)[1].strip()
            elif line.startswith('Requires:'):
                dep = line.split(':', 1)[1].strip()
                # 只提取包名，不包含版本号
                dep_name = dep.split(' ')[0]
                requires.append(dep_name)
            elif line.startswith('BuildRequires:'):
                dep = line.split(':', 1)[1].strip()
                # 只提取包名，不包含版本号
                dep_name = dep.split(' ')[0]
                build_requires.append(dep_name)

    return name, version, requires, build_requires

def find_source_tarball(name, version):
    """
    根据包名和版本在 SOURCES_DIR 中查找对应的源码压缩包
    """
    pattern = f"{name}-{version}.tar.gz"
    tarball_path = os.path.join(SOURCES_DIR, pattern)
    if os.path.isfile(tarball_path):
        return tarball_path
    else:
        return None

def generate_readme(name, version, dependencies):
    """
    生成 README.md 内容
    """
    readme_content = f"""# {name}

## 版本

- 名称: {name}
- 版本: {version}

## 依赖

"""
    for dep in dependencies:
        # 仅列出 ROS 相关的依赖
        if dep.startswith('ament-') or dep.startswith('ros-'):
            readme_content += f"- {dep}\n"

    return readme_content

def sanitize_repo_name(name):
    """
    根据需求，将包名转换为仓库名，移除 'ros-jazzy-' 前缀和版本号
    例如：'ros-jazzy-ament-cmake-auto' -> 'ament-cmake-auto'
    """
    # 移除 'ros-jazzy-' 前缀
    if name.startswith('ros-jazzy-'):
        name = name[len('ros-jazzy-'):]
    return name

def create_gitee_repo(repo_name):
    """
    在 Gitee 上创建一个新的公开仓库
    """
    if GITEE_ORG:
        # 创建组织下的仓库
        url = urljoin(GITEE_API_BASE, f'orgs/{GITEE_ORG}/repos')
    else:
        # 创建个人仓库
        url = urljoin(GITEE_API_BASE, 'user/repos')

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'token {GITEE_TOKEN}'
    }

    data = {
        'name': repo_name,
        'private': False,  # 设置为 False 以创建公开仓库
        'auto_init': False,
        'description': f'Repository for {repo_name}'
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 201:
        repo_info = response.json()
        print(f"已在 Gitee 上创建仓库: {repo_info['full_name']}")
        return repo_info['ssh_url'], repo_info['html_url']
    else:
        print(f"创建仓库失败: {repo_name}, 错误信息: {response.json().get('message', '未知错误')}")
        return None, None

def main():
    # 初始化列表来保存成功上传的仓库链接
    uploaded_repos = []

    # 遍历 SPECS_DIR 中的所有 .spec 文件
    for spec_file in os.listdir(SPECS_DIR):
        if spec_file.endswith('.spec'):
            spec_path = os.path.join(SPECS_DIR, spec_file)
            name, version, requires, build_requires = extract_spec_info(spec_path)

            if not name or not version:
                print(f"无法从 {spec_file} 中提取名称或版本。跳过。")
                continue

            print(f"处理包: {name}, 版本: {version}")

            # 找到对应的源码压缩包
            tarball_path = find_source_tarball(name, version)
            if not tarball_path:
                print(f"未找到源码压缩包: {name}-{version}.tar.gz。跳过。")
                continue

            # 提取依赖项，只保留 ROS 相关的依赖
            dependencies = [dep for dep in requires + build_requires if dep.startswith('ros-jazzy-ament-') or dep.startswith('ament-') or dep.startswith('ros-')]

            # 生成 README.md 内容
            readme_content = generate_readme(name, version, dependencies)

            # 创建仓库目录
            repo_name = sanitize_repo_name(name)
            repo_dir = os.path.join(OUTPUT_DIR, repo_name)
            os.makedirs(repo_dir, exist_ok=True)

            # 复制源码压缩包和 .spec 文件
            shutil.copy(tarball_path, repo_dir)
            shutil.copy(spec_path, repo_dir)

            # 写入 README.md
            readme_path = os.path.join(repo_dir, 'README.md')
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)

            # 初始化 Git 仓库
            os.chdir(repo_dir)
            if not os.path.isdir(os.path.join(repo_dir, '.git')):
                os.system('git init')

            # 添加并提交文件
            os.system('git add .')
            # 检查是否有未提交的更改并提交
            commit_status = os.system('git diff --cached --quiet || git commit -m "Initial commit with source tarball, spec file, and README."')
            if commit_status != 0:
                print(f"包 {repo_name} 已经提交过，跳过提交步骤。")

            # 创建远程仓库
            remote_info = create_gitee_repo(repo_name)
            if not remote_info[0]:
                print(f"跳过推送 {repo_name} 到 Gitee。")
                continue

            ssh_url, html_url = remote_info

            # 添加远程仓库并推送
            os.system(f'git remote add origin {ssh_url}')
            os.system('git branch -M main')
            push_status = os.system('git push -u origin main')
            if push_status != 0:
                print(f"推送 {repo_name} 到 Gitee 失败。")
            else:
                print(f"已成功推送 {repo_name} 到 Gitee。")
                uploaded_repos.append(html_url)

    # 列出所有成功上传的 Gitee 仓库链接
    if uploaded_repos:
        print("\n以下是所有成功上传到 Gitee 的仓库链接：")
        for repo_link in uploaded_repos:
            print(repo_link)
    else:
        print("\n没有仓库被成功上传到 Gitee。")

    print("\n所有包的处理完成。")

if __name__ == "__main__":
    main()
➜  ~