# ROS Jazzy Porting to openEuler - Work Summary

## Goal

Try to port the full ROS Jazzy package set to openEuler 24.03, aiming to build a complete automated RPM build workflow from ROS package information, and ensure these batch-generated source archives and corresponding spec files can be built correctly on eulermaker.

## Completed Work

### Analyze ROS Jazzy Package Set

A script named `fetch_ros_packages.py.py` was used to implement the following:

- Retrieve all ROS package page links from the official ROS `sitemap.xml`
- Extract source repository URLs from ROS package pages
  - If a `jazzy` branch exists, automatically `clone` that branch; otherwise `clone` the main branch
- Automatically `git clone` these repositories to a specified local directory, with multithreading support

> Special note: usually these source packages are hosted on GitHub, but a small number are on GitLab and similar platforms. The script cannot identify those cases, so it may fail there. Since this is a minority, manual clone is acceptable.

Future work: this script is currently stable. A further improvement is planned to analyze each package's dependency chain and clarify relationships between core packages and second-/third-level dependencies, by storing dependencies in a dictionary like:

```
dependencies = {
    "mola_msgs": ["ament_cmake", "rosidl_default_generators"],
    "ament_cmake": [],
    "rosidl_default_generators": ["rosidl_default_runtime"]
}
```

Use topological sorting to parse the dependency graph and ensure packages are built in the correct order.

### RPM Package Build Workflow

This process involves two scripts: `process_ros_packages.sh`, `batch_process_packages.sh`

`process_ros_packages.sh`: this script uses `bloom-generate` to generate `.spec` files. Based on the generated `.spec`, it renames the `.spec` file and source package, archives them into `tar.gz`, then places the `.spec` file and source archive into the `SPECS` and `SOURCES` directories.

`batch_process_packages.sh`: when there are many packages in a folder (for example dozens or hundreds), this script can search in a specified directory (or current directory) for `CMakeLists.txt` and `package.xml` to determine whether a folder is a standard package, then use `parallel` for multithreaded processing of multiple ROS packages. The processing method is: under each ROS package's parent directory, call `~/process_ros_packages.sh` to generate RPM packages.
At the same time, this script supports detecting errors during build and recording them into log files:

- `missing_rosdeps.log`: records unresolved dependencies.
- `skipped_packages.log`: records packages skipped due to `bloom-generate` failures.

Future work: these two scripts are currently working well, so no further changes are planned.

### Automatically Upload to Gitee

> Since my openEuler runs in a virtual machine and has some network issues, I directly `scp` problematic files from `SOURCES` and `SPECS` on openEuler to local, then upload to Gitee locally.

This process depends on two scripts: `upload_to_gitee.py`, `make_gitee_repos_public.py`

`upload_to_gitee.py`: this script can create folders under a specified directory, extract package name, version, and dependencies from `.spec` files, rename folders, and generate a `README.md` containing package name and dependencies, for example:

```
ros-jazzy-image-publisher

Version

Name: ros-jazzy-image-publisher
Version: 5.0.6
Dependencies

ros-jazzy-camera-info-manager
ros-jazzy-cv-bridge
ros-jazzy-image-transport
ros-jazzy-rcl-interfaces
ros-jazzy-rclcpp
ros-jazzy-rclcpp-components
ros-jazzy-ament-package
ros-jazzy-ament-cmake-auto
ros-jazzy-camera-info-manager
ros-jazzy-cv-bridge
ros-jazzy-image-transport
ros-jazzy-rcl-interfaces
ros-jazzy-rclcpp
ros-jazzy-rclcpp-components
ros-jazzy-ament-lint-auto
ros-jazzy-ament-lint-common
ros-jazzy-ament-package
```

After completing these steps locally, repositories can be uploaded to Gitee in batch automatically, and corresponding Gitee links are printed.

After successful upload, another script is needed: `make_gitee_repos_public.py`.
Since repositories created and uploaded locally are personal repositories (private by default), eulermaker cannot access them, so repositories must be switched from private to public.
The main function of this script is to convert private repositories to public and output successful links that can be directly copied into eulermaker.

## Major Issues Already Solved

With the work above, it is now possible to automatically extract package names, dependency relationships, and repository URLs from ROS package indexes, automatically switch branches, clone locally, and generate RPM spec files with `bloom-generate`.
It can also automatically create corresponding repositories on Gitee and output links that can be directly imported into eulermaker.

## Main Existing Problems

1. openEuler distribution itself has serious missing-package issues.
2. Since `bloom` is not adapted for openEuler, dependency mapping can fail.

Current workaround is to manually add missing packages into upstream yaml files whenever `rosdep` reports them missing, but this is low-efficiency, so further automation is being considered.

## Next Plan

~~Plan to turn these capabilities into a tool for higher-efficiency packaging.~~

~~This tool should include:~~

~~- Automatically map all content from upstream yum repositories into upstream rosdep yaml files~~
~~- Automatically update yum and automatically update mappings in yaml files~~
~~- Automatically analyze dependency relationships and list package build order~~
~~- Automatically list missing dependency packages~~

Tool development is already completed: https://github.com/Sebastianhayashi/ros_openeuler_tool

At present, this function (mapping YUM repositories to rosdep (TODO)) is still incomplete, so further testing and development are needed.

## Additional Note

All scripts mentioned in this document can be found under `mechanism` in this repository.
