# Detect openEuler

> If you haven't read the README yet, I recommend checking that out first.

## Background

The purpose of this article is to enable the rospkg tool to correctly identify openEuler and its corresponding version number.
System and version used in the examples:

```
(toolchain) ➜  rcl_logging_interface git:(jazzy) ✗ cd
(toolchain) ➜  ~ cat /etc/openEuler-release
openEuler release 24.03 (LTS)
(toolchain) ➜  ~ cat /etc/os-release
NAME="openEuler"
VERSION="24.03 (LTS)"
ID="openEuler"
VERSION_ID="24.03"
PRETTY_NAME="openEuler 24.03 (LTS)"
ANSI_COLOR="0;31"

```

The goal is to achieve the following result: allowing the bloom tool to work with rospkg to identify openEuler:

```
(toolchain) ➜  rcl_logging_interface git:(jazzy) ✗ bloom-generate rosrpm --os-name openEuler --os-version 24.03 --ros-distro jazzy
ROS Distro index file associate with commit '0d9a6f9eea5073fc27bdaf0f5e242b9d0c1b8d4a'
New ROS Distro index url: 'https://raw.githubusercontent.com/ros/rosdistro/0d9a6f9eea5073fc27bdaf0f5e242b9d0c1b8d4a/index-v4.yaml'
==> Generating RPMs for openEuler:24.03 for package(s) ['rcl_logging_interface']
No homepage set
GeneratorError: Error running generator: Could not determine the installer for 'openEuler'

```

## Source Code Changes

The tool responsible for system identification is rospkg. Therefore, the first step in porting the entire toolchain is porting rospkg. We need to ensure that bloom can correctly identify our system.

The file in rospkg responsible for system detection is `os_detect.py`. We only need to modify this file, which is located at:

```
rospkg/src/rospkg/os_detect.py

```

You can view the specific patch [here](https://github.com/Sebastianhayashi/rospkg/commit/0ed4a19f12a065f8fea21cc540abf4c9b4c6f25b).

## Explanation of Changes

First change:

```
class OpenEuler(OsDetector):
    """
    Detect OpenEuler OS.
    """
    def __init__(self, release_file="/etc/openEuler-release"):
        self._release_info = read_os_release()
        self._release_file = release_file
    def is_os(self):
        return os.path.exists(self._release_file)
    def get_version(self):
        if self.is_os():
            return self._release_info["VERSION_ID"]
        raise OsNotDetected("called in incorrect OS")
    def get_codename(self):
        if self.is_os():
            return ""
        raise OsNotDetected('called in incorrect OS')

```

`is_os()` checks for the existence of `/etc/openEuler-release`, which is unique to openEuler. The logic here is that if this file exists, we can directly determine that the system is openEuler.
Next, `get_version()` calls `read_os_release()` and returns the `VERSION_ID`. This allows for the correct output of openEuler and its corresponding version number.

### Alternative Approaches

For rospkg, there is a generic class:

```
OsDetect.register_default("fedora", FdoDetect("fedora"))

```

This generic class uses `FdoDetect` to read `/etc/os-release`. If it reads `ID="fedora"`, it considers the system to be Fedora.

However, openEuler adopts a method similar to OpenSuse and Gentoo, defining an independent class to check for distribution-specific files. If there are no special considerations during porting, using `FdoDetect` could also be considered.

Second change:

Add a new constant `OS_OPENEULER = 'openEuler'` to let rospkg define the OS name as openEuler.

You can follow a similar pattern to define your own distribution.

Third change:

```
OsDetect.register_default(OS_OPENEULER, OpenEuler())

```

This syntax enables rospkg to attempt matching openEuler to `OpenEuler()` first during `detect_os()`, initiating the process.
When `OpenEuler().is_os()` returns `True`, openEuler becomes the first successfully matched OS. This ensures that rospkg prioritizes matching our distribution, avoiding conflicts with other systems.

## Testing

Use `pip install -e .` to install the ported code.
Enter a ROS package and use the following command (please modify according to your actual situation) to test if the output is correct:

```
bloom-generate rosrpm --os-name openEuler --os-version 24.03 --ros-distro jazzy

```

Expected behavior:

```
(toolchain) ➜  rcl_logging_interface git:(jazzy) ✗ bloom-generate rosrpm --os-name openEuler --os-version 24.03 --ros-distro jazzy
ROS Distro index file associate with commit '0d9a6f9eea5073fc27bdaf0f5e242b9d0c1b8d4a'
New ROS Distro index url: 'https://raw.githubusercontent.com/ros/rosdistro/0d9a6f9eea5073fc27bdaf0f5e242b9d0c1b8d4a/index-v4.yaml'
==> Generating RPMs for openEuler:24.03 for package(s) ['rcl_logging_interface']
No homepage set
GeneratorError: Error running generator: Could not determine the installer for 'openEuler'

```

## Additional Notes

The patch used in this article is sourced from: [https://github.com/ros-infrastructure/rospkg/commit/812e09840e3e264f87001f1557342b5265a3c403#diff-4ec3d8ff31d9d834ce01e10784e00d1ba38736582346ef8fa1610bc3a737d1cfL265-R721](https://github.com/ros-infrastructure/rospkg/commit/812e09840e3e264f87001f1557342b5265a3c403#diff-4ec3d8ff31d9d834ce01e10784e00d1ba38736582346ef8fa1610bc3a737d1cfL265-R721)