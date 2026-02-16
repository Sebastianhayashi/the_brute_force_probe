#!/bin/bash

# ===============================================
# 脚本名称: process_ros_packages.sh
# 描述:
#   自动化处理 ROS 包，生成 RPM 规范文件，并打包完整的源码包。
#
# 使用方法:
#   1. 将脚本保存为 process_ros_packages.sh。
#   2. 赋予执行权限：chmod +x process_ros_packages.sh
#   3. 在包含所有包子目录的根目录下运行脚本：./process_ros_packages.sh
#
# 需求:
#   - bloom 工具已安装。
#   - 所有包的源代码位于当前目录的子目录中。
# ===============================================

# 设置 SPECS 和 SOURCES 目录
SPECS_DIR="$HOME/rpmbuild/SPECS"
SOURCES_DIR="$HOME/rpmbuild/SOURCES"

# 获取当前工作目录
BASE_DIR="$(pwd)"

echo "当前工作目录：$BASE_DIR"
echo "----------------------------------------"

# 检查并创建 SPECS 目录
if [ ! -d "$SPECS_DIR" ]; then
    echo "SPECS 目录 $SPECS_DIR 不存在，正在创建..."
    mkdir -p "$SPECS_DIR"
    if [ $? -ne 0 ]; then
        echo "无法创建 SPECS 目录，请检查权限。"
        exit 1
    fi
fi

# 检查并创建 SOURCES 目录
if [ ! -d "$SOURCES_DIR" ]; then
    echo "SOURCES 目录 $SOURCES_DIR 不存在，正在创建..."
    mkdir -p "$SOURCES_DIR"
    if [ $? -ne 0 ]; then
        echo "无法创建 SOURCES 目录，请检查权限。"
        exit 1
    fi
fi

# 遍历当前目录下的所有子目录
for pkg_dir in "$BASE_DIR"/*/; do
    # 检查是否为目录
    if [ ! -d "$pkg_dir" ]; then
        continue
    fi

    # 去除尾部斜杠并获取包名
    pkg_dir=${pkg_dir%/}
    pkg_name=$(basename "$pkg_dir")
    echo "----------------------------------------"
    echo "处理包：$pkg_name"

    cd "$pkg_dir" || { echo "无法进入目录 $pkg_dir"; cd "$BASE_DIR"; continue; }

    # 执行 bloom-generate 命令
    echo "执行 bloom-generate 命令..."
    bloom-generate rosrpm --os-name openeuler --os-version 24.03 --ros-distro jazzy
    if [ $? -ne 0 ]; then
        echo "bloom-generate 失败，跳过包 $pkg_name"
        cd "$BASE_DIR"
        continue
    fi

    # 检查 rpm 目录是否存在
    RPM_DIR="$pkg_dir/rpm"
    if [ ! -d "$RPM_DIR" ]; then
        echo "rpm 目录不存在，跳过包 $pkg_name"
        cd "$BASE_DIR"
        continue
    fi

    TEMPLATE_SPEC="$RPM_DIR/template.spec"
    if [ ! -f "$TEMPLATE_SPEC" ]; then
        echo "template.spec 文件不存在，跳过包 $pkg_name"
        cd "$BASE_DIR"
        continue
    fi

    # 提取 Name 和 Version
    NAME=$(grep "^Name:" "$TEMPLATE_SPEC" | awk '{print $2}')
    VERSION=$(grep "^Version:" "$TEMPLATE_SPEC" | awk '{print $2}')

    if [ -z "$NAME" ] || [ -z "$VERSION" ]; then
        echo "无法提取 Name 或 Version，跳过包 $pkg_name"
        cd "$BASE_DIR"
        continue
    fi

    echo "包名：$NAME，版本：$VERSION"

    # 重命名 template.spec
    SPEC_NAME="${NAME}.spec"
    mv "$TEMPLATE_SPEC" "$RPM_DIR/$SPEC_NAME"
    if [ $? -ne 0 ]; then
        echo "无法重命名 spec 文件，跳过包 $pkg_name"
        cd "$BASE_DIR"
        continue
    fi

    # 复制 spec 文件到 SPECS 目录
    cp "$RPM_DIR/$SPEC_NAME" "$SPECS_DIR/"
    if [ $? -ne 0 ]; then
        echo "无法复制 spec 文件到 SPECS 目录，跳过包 $pkg_name"
        cd "$BASE_DIR"
        continue
    fi

    # 定义新的目录名称
    NEW_DIR_NAME="${NAME}-${VERSION}"
    TARGET_DIR="$BASE_DIR/$NEW_DIR_NAME"

    # 检查目标目录是否已存在
    if [ -d "$TARGET_DIR" ]; then
        echo "目标目录 $TARGET_DIR 已存在，正在删除旧目录..."
        rm -rf "$TARGET_DIR"
        if [ $? -ne 0 ]; then
            echo "无法删除旧的目标目录，跳过包 $pkg_name"
            cd "$BASE_DIR"
            continue
        fi
    fi

    # 复制包目录到新的目标目录
    echo "复制包目录到目标目录 $TARGET_DIR..."
    cp -r "$pkg_dir" "$TARGET_DIR/" | tee -a "$BASE_DIR/process_ros_packages_cp.log"
    if [ $? -ne 0 ]; then
        echo "无法复制包目录到目标目录，跳过包 $pkg_name"
        cd "$BASE_DIR"
        continue
    fi

    # 压缩重命名后的目录
    TAR_FILE="${NEW_DIR_NAME}.tar.gz"
    echo "压缩目录 $NEW_DIR_NAME 到 $TAR_FILE..."
    tar -czvf "$TAR_FILE" -C "$BASE_DIR" "$NEW_DIR_NAME" | tee -a "$BASE_DIR/process_ros_packages_tar.log"
    if [ $? -ne 0 ]; then
        echo "无法压缩目录，跳过包 $pkg_name"
        rm -rf "$TARGET_DIR"
        cd "$BASE_DIR"
        continue
    fi

    # 复制压缩文件到 SOURCES 目录
    echo "复制压缩文件 $TAR_FILE 到 $SOURCES_DIR..."
    cp "$TAR_FILE" "$SOURCES_DIR/" | tee -a "$BASE_DIR/process_ros_packages_cp.log"
    if [ $? -ne 0 ]; then
        echo "无法复制压缩文件到 SOURCES 目录，跳过包 $pkg_name"
        rm -rf "$TARGET_DIR"
        rm -f "$TAR_FILE"
        cd "$BASE_DIR"
        continue
    fi

    # 清理临时文件
    rm -f "$TAR_FILE"
    rm -rf "$TARGET_DIR"

    echo "包 $pkg_name 处理完成。"
    cd "$BASE_DIR"
done

echo "所有包处理完毕。"