#!/usr/bin/env bash
#
# batch_process_parent.sh
#
# 功能：
#   1) 在当前目录(或指定目录)下递归搜索所有 ROS 包（满足 CMakeLists.txt + package.xml）。
#   2) 并行地在其父目录执行 ~/process_ros_packages.sh <子目录> 来生成 RPM。
#   3) 如果发现 "bloom-generate 失败，跳过包 <pkg>"，则自动跳过并记录到 ~/missing_deps/skipped_packages.log。
#   4) 若脚本输出 "Could not resolve rosdep key 'xxx'"，则将 xxx 去重写入 ~/missing_deps/missing_rosdeps.log。
#
# 用法：
#   ./batch_process_parent.sh [search_root]
#   - search_root: 可选，指定要搜索的根目录；不指定时默认当前目录。
#
# 注意：
#   - ~/process_ros_packages.sh 必须存在并可执行，且支持形如 ./process_ros_packages.sh <pkg_subdir> 的调用。
#   - 需要并行可安装 parallel (dnf或apt安装)，并注意 -j 并行度设置。
#   - 如果某个包 Bloom 失败，在输出出现 "bloom-generate 失败，跳过包 <pkg>"，会自动记录跳过。

###############################################################################
# 1. 环境检查
###############################################################################
if [[ ! -f ~/process_ros_packages.sh ]]; then
  echo "[ERROR] ~/process_ros_packages.sh 不存在，请放到 HOME 目录并确保可执行。"
  exit 1
fi

# 搜集缺失依赖的日志目录和文件
MISSING_DEPS_DIR="$HOME/missing_deps"
mkdir -p "$MISSING_DEPS_DIR"

MISSING_ROSDEPS_LOG="$MISSING_DEPS_DIR/missing_rosdeps.log"
touch "$MISSING_ROSDEPS_LOG"

SKIPPED_PACKAGES_LOG="$MISSING_DEPS_DIR/skipped_packages.log"
touch "$SKIPPED_PACKAGES_LOG"

# 并行度(可根据 CPU 核数和需求调整)
PARALLEL_JOBS=32

# 若用户指定了搜索根目录，则用之，否则用当前目录
SEARCH_ROOT="${1:-$PWD}"


###############################################################################
# 2. 判断某目录是否为 ROS 包 (同时存在 CMakeLists.txt & package.xml)
###############################################################################
function is_ros_package() {
  local dir="$1"
  [[ -f "$dir/CMakeLists.txt" && -f "$dir/package.xml" ]]
}


###############################################################################
# 3. 递归收集函数：collect_ros_packages
#    - 遍历 search_root 下所有子目录，遇到是ROS包就保存到 ALL_PACKAGES 数组
###############################################################################
ALL_PACKAGES=()

function collect_ros_packages() {
  local dir="$1"

  # 若是 ROS 包
  if is_ros_package "$dir"; then
    ALL_PACKAGES+=("$dir")
  else
    # 否则继续遍历子目录
    local subdirs
    mapfile -t subdirs < <( find "$dir" -maxdepth 1 -mindepth 1 -type d 2>/dev/null )
    for sd in "${subdirs[@]}"; do
      collect_ros_packages "$sd"
    done
  fi
}


###############################################################################
# 4. 并行调用的函数：run_parent_process_script
#    - 参数：一个ROS包的绝对路径 (如 /home/yuyu/A/asr_state_machine)
#    - 做法：
#       1) 取得 parent_dir = dirname(该路径)
#       2) 取得 pkg_basename = basename(该路径)
#       3) 复制 ~/process_ros_packages.sh 到 parent_dir
#       4) 在 parent_dir 下执行 ./process_ros_packages.sh pkg_basename (2>&1)
#       5) 解析脚本输出：
#          a) 若出现 "bloom-generate 失败，跳过包 <pkg>"，记录并跳过
#          b) 若出现 "Could not resolve rosdep key 'xxx'"，记录 xxx (去重)
###############################################################################
function run_parent_process_script() {
  local pkg_path="$1"
  local parent_dir
  parent_dir="$(dirname "$pkg_path")"

  local pkg_basename
  pkg_basename="$(basename "$pkg_path")"

  # 拷贝脚本到 parent_dir
  cp -f ~/process_ros_packages.sh "$parent_dir"

  # 在 parent_dir 执行脚本，传递 pkg_basename 作为参数
  local script_output
  script_output="$(
    cd "$parent_dir" || exit 1
    ./process_ros_packages.sh "$pkg_basename" 2>&1
  )"

  # 1) 检查是否有 "bloom-generate 失败，跳过包 xxx"
  #    格式示例： "Try to resolve the problem with rosdep and then continue.
  #    Continue [Y/n]? ^Cbloom-generate 失败，跳过包 ackermann_controller"
  #
  #    我们用 grep + 正则去提取 "跳过包 <xxx>"
  local skip_pkg_name
  skip_pkg_name="$(echo "$script_output" | grep -oP "(?<=跳过包 )\S+")"

  if [[ -n "$skip_pkg_name" ]]; then
    # 说明 bloom-generate 失败，需要跳过
    echo "[SKIP] 检测到 bloom-generate 失败，跳过包: $skip_pkg_name"
    echo "[SKIP] 检测到 bloom-generate 失败，跳过包: $skip_pkg_name" >> "$SKIPPED_PACKAGES_LOG"
  fi

  # 2) 检查 "Could not resolve rosdep key 'xxx'"
  local missing_keys
  missing_keys=$(echo "$script_output" | grep -oP "Could not resolve rosdep key '\K[^']+")

  if [[ -n "$missing_keys" ]]; then
    for key in $missing_keys; do
      if ! grep -qx "$key" "$MISSING_ROSDEPS_LOG"; then
        echo "$key" >> "$MISSING_ROSDEPS_LOG"
      fi
    done
  fi
}

# 导出函数和必要变量给 parallel 子进程使用
export -f run_parent_process_script
export MISSING_DEPS_DIR MISSING_ROSDEPS_LOG SKIPPED_PACKAGES_LOG


###############################################################################
# 5. 主流程
###############################################################################
echo "[INFO] 开始在 $SEARCH_ROOT 下收集 ROS 包..."
collect_ros_packages "$SEARCH_ROOT"

if [[ ${#ALL_PACKAGES[@]} -eq 0 ]]; then
  echo "[INFO] 未找到任何 ROS 包。"
  exit 0
fi

echo "[INFO] 共收集到 ${#ALL_PACKAGES[@]} 个 ROS 包，准备并行执行..."

# 并行执行 run_parent_process_script
printf '%s\n' "${ALL_PACKAGES[@]}" \
  | parallel -j "$PARALLEL_JOBS" run_parent_process_script {}

echo "[INFO] 所有执行完成，请查看 ~/rpmbuild/SPECS 和 ~/rpmbuild/SOURCES 确认打包结果。"
echo "[INFO] 若有缺失的依赖，可在 $MISSING_ROSDEPS_LOG 查看。"
echo "[INFO] 若有 bloom-generate 失败的包，可在 $SKIPPED_PACKAGES_LOG 查看。"
exit 0