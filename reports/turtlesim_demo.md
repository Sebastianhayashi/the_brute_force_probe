# Running the Turtlesim Demo on openEuler

## Overview

This document mainly explains how to configure ROS Jazzy on openEuler 24.03 LTS (x86 architecture) and successfully run the classic turtlesim demo, so readers can quickly verify the feasibility of ROS on openEuler and get started.

## Environment

- System: openEuler 24.03 LTS
- Architecture: x86
- ROS version: Jazzy

## Enable the Repository

1. Create a new `.repo` file to add the package source. Use the following commands:

```
cd /etc/yum.repos.d
sudo vi openEuler-jazzy.repo
```

2. The content of `openEuler-jazzy.repo` is:

```
[openEuler-Jazzy]
name=openEuler-Jazzy
baseurl=https://eulermaker.compass-ci.openeuler.openatom.cn/api/ems1/repositories/jazzy_ament_package/openEuler%3A24.03-LTS/x86_64/
enabled=1
gpgcheck=0
```
3. After adding it successfully, update with dnf:

```
sudo dnf clean all
sudo dnf makecache

sudo dnf update --nobest
```
## Install ROS Jazzy

Install the full ROS Jazzy package set:
```
sudo dnf install "ros-jazzy*" --skip-broken -y
```
There are still conflict packages in the repository. Seeing many conflict errors is expected behavior. You can ignore them during reproduction, and dnf will automatically install whatever can be installed.

## Run the Turtlesim Demo

1. After installation, activate the ROS environment:

```
source /opt/ros/jazzy/setup.zsh
```

> If your default shell is bash, use `setup.bash`

2. Then make sure you open two terminal windows in a graphical desktop environment:

```
# terminal window1
ros2 run turtlesim turtle_teleop_key

# terminal window2
ros2 run turtlesim turtlesim_node
```
3. Use the first window to move the turtle, and you should see the turtle moving normally.

Expected behavior:

![alt text](./img/turtlesim.png)

## Additional Notes

1. **tbb conflict during dnf update**

It is expected to see a tbb conflict during dnf update. This is because the tbb package provided by openEuler does not meet ROS Jazzy requirements, so a newer tbb version exists in the repo. If conflict happens, you can ignore it directly.

2. **Many conflict messages when downloading packages with dnf**

Seeing many conflicts while downloading ROS Jazzy packages with dnf is expected, because the current repo packages are only enough to support launching the turtlesim demo, and many conflict packages are still unresolved.

## Related Documents

We are currently planning documents related to ROS Jazzy packaging:

- ROS official toolchain research
- Full packaging workflow on eulermaker
- Principles and notes for derivative tools
- ...

This series aims to introduce the official ROS packaging workflow in detail and explain how the turtlesim ROS environment in this document was built.
