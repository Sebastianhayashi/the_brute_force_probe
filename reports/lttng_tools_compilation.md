# LTTng-Tools Report


## Background

At present, the reason most package dependencies are not closed-loop is that `rmw-fastrtps-shared-cpp` cannot be built normally, with the error:

```
Error:
236
2024-12-29 14:26:08 Problem: conflicting requests
237
2024-12-29 14:26:08 - nothing provides lttng-tools needed by ros-jazzy-tracetools-8.5.0-0.oe2403.x86_64 from 0
238
2024-12-29 14:26:08 (try to add '--skip-broken' to skip uninstallable packages or '--nobest' to use not only best candidate packages)
```

So we need to resolve the `lttng-tools` issue. Since openEuler upstream does not directly provide the `lttng-tools` package, this dependency must be built manually for `ros-jazzy-tracetools`, which is why this report exists.

This report mainly records how to compile LTTng-Tools and how to solve the issue above.

## Build and Install LTTng-UST

Since openEuler upstream lacks `lttng-ust`, we manually compile and install a newer version.

### babeltrace2

`liburcu` is a prerequisite for babeltrace2, so build babeltrace2 first.

Dependencies:

- elfutils-libelf-devel
- libdwarf-devel
- libdwarf
- libdwarf-tools
- elfutils
- elfutils-libelf
- elfutils-libelf-devel
- elfutils-devel

```
git clone https://git.efficios.com/babeltrace.git
git checkout stable-2.0
./bootstrap
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
```
 
### liburcu

Since openEuler upstream lacks `liburcu`, we need to manually compile it first.

Dependencies:

- numactl-devel
- numactl-libs

```
git clone https://github.com/urcu/userspace-rcu.git
cd userspace-rcu
./bootstrap
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install

export PKG_CONFIG_PATH=/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH
export PATH=/usr/local/bin:$PATH
```

### LTTng-UST

Because the `lttng-ust` version in openEuler repositories is relatively old (2.13.7), we need to manually compile and install a newer version.

Dependencies:
- liburcu >= 0.12
- libnuma
- asciidoc
- xmlto
- babeltrace2
- elfutils-libelf-devel
- libdwarf-devel
- libdwarf
- libdwarf-tools
- elfutils
- elfutils-libelf
- elfutils-libelf-devel
- elfutils-devel

```
git clone https://github.com/lttng/lttng-ust.git
cd lttng-ust
git checkout master

./bootstrap
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
sudo ldconfig
cd ..

pkg-config --modversion lttng-ust

# It should output 2.14.x or higher, which means installation succeeded.
```

## Build and Install LTTng-Tools

Dependencies

Make sure the following dependencies are installed:
- libtool
- ibtool-ltdl-devel
- bison
- flex
- libxml2
- libxml2-devel
- asciidoc
- xmlto
- babeltrace2
- liburcu
- libnuma

## Clone and Build LTTng-Tools

```
git clone https://github.com/lttng/lttng-tools.git
cd lttng-tools
mkdir build && cd build
cmake ..

./bootstrap
./configure --prefix=/usr/local
make -j$(nproc)
sudo make install
sudo ldconfig
```

After all steps are completed, verify whether installation succeeded.

```
lttng --version
```

It should output the LTTng-Tools version information, which indicates successful installation.

## Additional Note

Since the above packages are not ROS packages, the process above needs to be written into `ros-jazzy-tracetools.spec`, and this is still in progress.
