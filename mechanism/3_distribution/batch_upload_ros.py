!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import requests
import configparser
from urllib.parse import urlparse

from copr.v3 import Client
from copr.v3 import exceptions as copr_exceptions
from copr.v3.helpers import config_from_file

# -- 日志配置
logging.basicConfig(
    level=logging.INFO,   # 如果需要调试详细信息，可改为 logging.DEBUG
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("batch_upload_ros.log"),
        logging.StreamHandler()
    ]
)

# -- Copr(EUR) 配置文件
COPR_CONFIG_PATH = os.path.expanduser("~/.config/copr")

# -- 目标分支名称
TARGET_BRANCH = "Multi-Version_ros-jazzy_openEuler-24.03-LTS"

# -- 生成的 JSON 文件名
PACKAGES_JSON_FILE = "packages_info.json"

def read_copr_config(config_path):
    """
    从 ~/.config/copr 中读取 copr-cli 配置
    """
    try:
        config = config_from_file(config_path)
        return config
    except Exception as e:
        logging.error(f"读取 Copr 配置失败: {e}")
        return None

def get_gitee_repos(username, token):
    """
    获取指定 Gitee 用户的所有仓库
    """
    page = 1
    per_page = 100
    all_repos = []
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/json'
    }
    while True:
        url = f"https://gitee.com/api/v5/users/{username}/repos"
        params = {'page': page, 'per_page': per_page}
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            logging.error(f"获取仓库列表失败({resp.status_code}): {resp.text}")
            break

        data = resp.json()
        if not data:
            break

        all_repos.extend(data)
        logging.debug(f"获取第 {page} 页，共 {len(data)} 个仓库")
        page += 1
    return all_repos

def check_branch_exists(repo_full_name, branch, gitee_token):
    """
    判断仓库是否存在目标分支
    """
    headers = {
        'Authorization': f'token {gitee_token}',
        'Accept': 'application/json'
    }
    url = f"https://gitee.com/api/v5/repos/{repo_full_name}/branches/{branch}"
    resp = requests.get(url, headers=headers)
    return (resp.status_code == 200)

def command_createjson(gitee_username, gitee_token):
    """
    第一步：自动生成 packages_info.json
    1. 从 Gitee 拉取所有仓库
    2. 若存在目标分支，则构造 https://gitee.com/<full_name>.git 作为 clone_url
    3. spec 名称为 <repo_name>.spec
    4. 最终写到 packages_info.json
    """
    # -- 读取 Copr 配置 (可选)
    if os.path.exists(COPR_CONFIG_PATH):
        config = read_copr_config(COPR_CONFIG_PATH)
        if config:
            logging.info("成功读取 Copr(EUR) 配置。")
        else:
            logging.error("Copr 配置读取失败，继续执行但可能会影响后续上传。")
    else:
        logging.warning(f"未找到 Copr 配置文件: {COPR_CONFIG_PATH}")

    # -- 获取所有 Gitee 仓库
    repos = get_gitee_repos(gitee_username, gitee_token)
    logging.info(f"从 Gitee 用户 {gitee_username} 获取到 {len(repos)} 个仓库。")

    packages_info = []

    for repo in repos:
        repo_full_name = repo.get("full_name")   # e.g. "Sebastianlin/urg_c"
        repo_name = repo.get("name")             # e.g. "urg_c"
        if not repo_full_name or not repo_name:
            logging.warning(f"仓库数据缺少 'full_name' 或 'name' 字段, 跳过: {repo}")
            continue

        # -- 强制使用 HTTPS URL: https://gitee.com/<repo_full_name>.git
        clone_url = f"https://gitee.com/{repo_full_name}.git"

        # -- 检查是否存在目标分支
        if check_branch_exists(repo_full_name, TARGET_BRANCH, gitee_token):
            package_name = f"Ros-jazzy-{repo_name}"
            spec_name = f"{repo_name}.spec"

            pkg = {
                "repo_name"    : repo_name,
                "full_name"    : repo_full_name,
                "clone_url"    : clone_url,
                "package_name" : package_name,
                "spec_name"    : spec_name
            }
            packages_info.append(pkg)
            logging.info(f"仓库 {repo_full_name} 存在分支 {TARGET_BRANCH}, 加入列表 => {package_name}")
        else:
            logging.info(f"仓库 {repo_full_name} 无分支 {TARGET_BRANCH}, 跳过.")

    # -- 写出 JSON 文件
    with open(PACKAGES_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(packages_info, f, ensure_ascii=False, indent=2)
    logging.info(f"已将 {len(packages_info)} 个包信息写入 {PACKAGES_JSON_FILE}")

def command_upload(gitee_username, gitee_token):
    """
    第二步：从 packages_info.json 读取包信息，逐个提交到 EUR (Copr)
    """
    # -- 检查并读取 Copr 配置
    if not os.path.exists(COPR_CONFIG_PATH):
        logging.error(f"Copr 配置文件不存在: {COPR_CONFIG_PATH}")
        return
    config = read_copr_config(COPR_CONFIG_PATH)
    if not config:
        logging.error("Copr 配置读取失败，无法初始化 Copr 客户端。")
        return

    # -- 初始化 Copr 客户端
    try:
        client = Client(config)
        logging.info("成功初始化 Copr 客户端。")
    except Exception as e:
        logging.error(f"初始化 Copr 客户端失败: {e}")
        return

    eur_project  = "Jazzy_Porting"  # 您在 Copr/EUR 上创建的项目名称

    # -- 获取 Copr 项目
    try:
        ownername = config['username']
        if not ownername:
            logging.error("配置文件中缺少 'username' 字段。")
            return
        project_obj = client.project_proxy.get(ownername=ownername, projectname=eur_project)
        logging.info(f"已获取到 Copr(EUR) 项目: {eur_project}")
    except copr_exceptions.CoprNoResultException:
        logging.error(f"项目 {eur_project} 不存在，请先创建")
        return
    except Exception as e:
        logging.error(f"获取 Copr 项目失败: {e}")
        return

    # -- 读取 packages_info.json
    if not os.path.exists(PACKAGES_JSON_FILE):
        logging.error(f"未找到 {PACKAGES_JSON_FILE}, 请先执行 createjson")
        return
    try:
        with open(PACKAGES_JSON_FILE, "r", encoding="utf-8") as f:
            packages_list = json.load(f)
        logging.info(f"从 {PACKAGES_JSON_FILE} 读取到 {len(packages_list)} 个包。")
    except json.JSONDecodeError as e:
        logging.error(f"读取 {PACKAGES_JSON_FILE} 失败: {e}")
        return
    except Exception as e:
        logging.error(f"读取 {PACKAGES_JSON_FILE} 时发生错误: {e}")
        return

    logging.info(f"开始从 {PACKAGES_JSON_FILE} 中读取 {len(packages_list)} 个包并上传到 EUR...")

    # -- 逐个包进行提交
    for pkg in packages_list:
        package_name = pkg.get("package_name")
        clone_url    = pkg.get("clone_url")
        spec_name    = pkg.get("spec_name")

        # 检查必要字段
        if not package_name or not clone_url or not spec_name:
            logging.warning(f"包信息不完整, 跳过: {pkg}")
            continue

        # 再次确认 clone_url 是 https
        if not (clone_url.startswith("http://") or clone_url.startswith("https://")):
            logging.error(f"包 {package_name} 的 clone_url 非 https URL: {clone_url}, 跳过.")
            continue

        # -- 构造 source_dict
        source_type = "scm"
        source_dict = {
            "clone_url"   : clone_url,
            "committish"  : TARGET_BRANCH,  # 分支名或 commit id
            "subdirectory": "",
            "spec"        : spec_name,
            "scm_type"    : "git"
        }

        logging.info(f"开始提交包: {package_name} => {clone_url}")
        try:
            build = client.package_proxy.add(
                ownername=ownername,
                projectname=eur_project,
                packagename=package_name,
                source_type=source_type,
                source_dict=source_dict
            )
            logging.info(f"包 {package_name} 提交成功, build_id={build.id}")
        except copr_exceptions.CoprException as e:
            logging.error(f"提交包 {package_name} 失败: {e}")
        except Exception as e:
            logging.error(f"提交包 {package_name} 时发生未知错误: {e}")

    logging.info("所有包都已尝试提交完毕。")

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python batch_upload_ros.py createjson  # 生成 packages_info.json")
        print("  python batch_upload_ros.py upload      # 读取 packages_info.json, 批量上传包")
        sys.exit(1)

    mode = sys.argv[1]
    gitee_username = os.environ.get("GITEE_USERNAME", "Sebastianlin")
    gitee_token    = os.environ.get("GITEE_TOKEN", "")

    if mode == "createjson":
        command_createjson(gitee_username, gitee_token)
    elif mode == "upload":
        command_upload(gitee_username, gitee_token)
    else:
        print("未知命令:", mode)
        sys.exit(1)

if __name__ == "__main__":
    main()