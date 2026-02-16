# Porting rosdep and rosdistro to openEuler

## Porting Strategy

### rosdep Layer

Porting `rosdep` involves not only `rosdep` itself but also `rosdistro`.
First, for `rosdep`, it needs to correctly identify openEuler or other non-official distributions. This part only requires modifying `redhat.py`.

The main file to modify is located at this path: `src/rosdep2/platforms/redhat.py`

* Add constant: `OS_OPENEULER = 'openEuler'`
* Add function: `register_openeuler(context)`
* Register multiple install keys for openEuler


* Add `register_openeuler(context)`
* Enable `rosdep` to recognize openEuler during the platform registration phase


* Add `register_rhel_clone(context, 'openEuler')`
* This indicates that openEuler does not follow the "rhel clone" alias and is treated as an independent OS.



For more detailed content, please check [here](https://github.com/Sebastianhayashi/rosdep/commit/fd4978b827ff389c55ead0ce03817fb5613b03c4).

### rosdistro Layer

For `rosdistro`, you also need to fork a copy from the official repository to your own account and modify the corresponding yaml files. The official `rosdistro` repository contains configuration files and related information for different ROS distributions, listing all released ROS packages and their dependencies.
The parts that need changing involve finding the folder corresponding to the version you want to port (taking `jazzy` as an example here) and supplementing `base.yaml` and `python.yaml`.

Next, add the corresponding distribution and its version to `jazzy/distribution.yaml` under `rosdistro`, like so:

```
%YAML 1.1
# ROS distribution file
# see REP 143: http://ros.org/reps/rep-0143.html
---
release_platforms:
  debian:
  - bookworm
  rhel:
  - '9'
  ubuntu:
  - noble
  openeuler:
  - '24.03'
  ...

```

Added:

```
  openeuler:
  - '24.03'

```

Please modify this according to your specific distribution situation.

Here, I have additionally created an automation script; the workflow is as follows:

1. Read the official `base.yaml` file in that folder.
2. Sequentially look up the defined package names for each key.
3. After finding the package name, run `dnf list <pkg>` one by one.
4. If it exists, record it; if not, record it in `fail_list.txt`.

This workflow allows for the automated update of content in the yaml.

Please view the script [here](https://www.google.com/search?q=../Scripts/%2520auto_generate_openeuler_yaml.py).

> Here, `rosdistro` refers to [https://github.com/ros/rosdistro](https://github.com/ros/rosdistro), not the tool.

Next, what needs to be changed is: `rosdep/sources.list.d/20-default.list`
Change all links in this file to the links in your own repository.

> Note: If your system is a custom distribution, you need to supplement `base.yaml`, etc., and modify `20-default.list` to point to the yaml links in your repository.

## Additional Notes

Original patch: [https://github.com/ros-infrastructure/rosdep/commit/139dde1bfa4cb58f6cfc6ede07f297c25c3de236#diff-0beed7b5444dff2fafbee569654182570dc1046fe8ce9f6b815014234e7e5ec7L37-R83](https://github.com/ros-infrastructure/rosdep/commit/139dde1bfa4cb58f6cfc6ede07f297c25c3de236#diff-0beed7b5444dff2fafbee569654182570dc1046fe8ce9f6b815014234e7e5ec7L37-R83