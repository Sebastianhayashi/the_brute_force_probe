#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
auto_generate_openeuler_yaml.py

功能:
1) 读取官方 base.yaml (或其它 rosdep YAML)
2) 对每个 rosdep key, 按指定的 fallback OS 顺序 (rhel->fedora->arch->...等) 依序查找已经定义的包名.
3) 一旦找到, 用 dnf list <pkg> 测试 openEuler 下是否存在.
4) 若全部存在 => 在 rosdep key 下写 `openeuler: [...]`; 若失败 => 跳过, 记入 fail_list.txt
5) 输出 base_openeuler.yaml + fail_list.txt, 并在命令行打印调试日志

依赖:
- Python 3 + PyYAML
- openEuler 系统(已安装 dnf), dnf list 命令可用

注意:
- 与之前的 fallback 脚本类似, 但改为写 "openeuler:" 而非 "openEuler:"
  这样与 rosdep 安装器 key (openeuler) 小写一致, 避免大小写冲突
"""

import os
import sys
import yaml
import subprocess

# 输入/输出文件
IN_FILE = "base.yaml"  # 原始 rosdep YAML
OUT_FILE = "base_openeuler.yaml"
FAIL_FILE = "fail_list.txt"

# 从这些 OS 依次尝试获取包名 -> 检测
FALLBACK_OSES = ["rhel", "fedora", "arch", "debian", "ubuntu", "gentoo", "nixos"]

def dnf_check_package(pkg):
    """
    执行 dnf list <pkg>, 若 returncode=0 且 stdout包含 pkg，则返回 True；否则 False.
    并在控制台打印简单日志。
    """
    cmd = ["dnf", "list", pkg]
    print(f"    [CMD] {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and pkg in r.stdout:
            print(f"    FOUND package: {pkg}")
            return True
        else:
            print(f"    NOT found: {pkg}, returncode={r.returncode}")
            return False
    except Exception as e:
        print(f"    ERROR while checking {pkg}: {e}")
        return False

def main():
    if not os.path.exists(IN_FILE):
        print(f"[ERROR] input file {IN_FILE} not found.")
        sys.exit(1)

    # 读取 base.yaml
    with open(IN_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not data or not isinstance(data, dict):
        print(f"[WARN] {IN_FILE} is empty or not valid.")
        data = {}

    fail_list = []
    changed_count = 0
    processed_count = 0

    for rosdep_key, os_map in data.items():
        if not isinstance(os_map, dict):
            continue
        # 若已有 'openeuler:' 则不覆盖
        if "openeuler" in os_map:
            continue

        # 依次 fallback
        fallback_found = False
        fallback_pkgs = None
        for fallback_os in FALLBACK_OSES:
            if fallback_os in os_map:
                fallback_pkgs = os_map[fallback_os]
                # 可能是字符串/列表
                if isinstance(fallback_pkgs, str):
                    fallback_pkgs = [fallback_pkgs]
                elif not isinstance(fallback_pkgs, list):
                    fallback_pkgs = None
                fallback_found = True
                break

        if not fallback_found or fallback_pkgs is None:
            # 没定义 rhel/fedora/... => 跳过
            continue

        processed_count += 1
        print(f"\n=== Key: {rosdep_key}, fallback_os => {fallback_os}, pkgs => {fallback_pkgs}")

        # 检测 pkg
        all_ok = True
        for pkg in fallback_pkgs:
            if not dnf_check_package(pkg):
                all_ok = False
                break

        if all_ok:
            # 全部都在 dnf list 里 => openeuler:
            os_map["openeuler"] = fallback_pkgs
            changed_count += 1
            print(f"  => SUCCESS, set openeuler => {fallback_pkgs}")
        else:
            # 记录到 fail_list
            fail_list.append(rosdep_key)
            print(f"  => FAIL, skip adding openeuler")

    # 写出 base_openeuler.yaml
    print(f"\nWriting {OUT_FILE} ...")
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, sort_keys=False)

    # 写 fail_list.txt
    print(f"Writing {FAIL_FILE}, total fails={len(fail_list)}")
    with open(FAIL_FILE, 'w', encoding='utf-8') as f:
        for k in fail_list:
            f.write(k + "\n")

    print(f"\n=== Done ===")
    print(f"Processed {processed_count} keys that had fallback packages, {changed_count} success => 'openeuler:' added.")
    print(f"Fail list has {len(fail_list)} => see {FAIL_FILE}.\n")

if __name__ == "__main__":
    main()