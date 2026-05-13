# Installation

Get from a fresh Ubuntu 24.04 machine to a built `bar_ws` in ~15 minutes.

## System requirements

| Item | Required | Reason |
|---|---|---|
| Ubuntu 24.04 LTS | yes | Jazzy is only packaged for noble |
| ROS 2 Jazzy | yes | every controller / message in this repo |
| C++20 compiler (gcc ≥ 13) | yes | `bar_common` and controllers use C++20 |
| Python ≥ 3.12 | yes | shipped with Ubuntu 24.04; needed for `bar_policy` |
| PREEMPT_RT kernel | recommended | hard real-time guarantees on real hardware |
| `libglfw3-dev` | for sim | required by `mujoco_sim_ros2` viewer |
| Display server | for sim | `mujoco_sim` opens a GLFW window |

:::tip[Docker-on-22.04 alternative]
The project targets Jazzy-on-24.04. Onboard computers stuck on Ubuntu 22.04
(notably the Jetson, which lags on vendor-supported Ubuntu releases) run a
**Jazzy-on-24.04 container**. The host OS only needs a real-time-capable
kernel, the right device permissions, and a container runtime — ROS itself
lives inside the container. See `bar_bringup_lite` for the docker-run
invocation template.
:::

## 1. Install ROS 2 Jazzy

Follow the [official docs](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html).
Short form:

```sh
sudo apt update && sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install -y ros-jazzy-desktop ros-dev-tools
```

## 2. Install workspace prerequisites

```sh
sudo apt install -y \
    python3-colcon-common-extensions \
    python3-vcstool \
    python3-rosdep \
    libglfw3-dev      # for mujoco_sim_ros2
sudo rosdep init || true
rosdep update
```

## 3. Clone and import dependencies

```sh
mkdir -p ~/bar_ws/src && cd ~/bar_ws/src
git clone https://github.com/T-K-233/bar_ros2.git
vcs import < bar_ros2/bar.repos
```

`bar.repos` vcs-imports four upstream dependencies:

:::warning[Optional: skip the EtherCAT path]
`ethercat_driver_ros2` needs `libethercat` compiled from the IgH EtherLAB
master — there's no apt package. If you're only working with Lite, you can
defer that build step:

```sh
# Skip building the EtherCAT subtree by passing --packages-skip later.
```

The Lite bringup does not depend on EtherCAT.
:::

## 4. Resolve rosdeps

```sh
cd ~/bar_ws
rosdep install --from-paths src --ignore-src -y \
    --skip-keys "libethercat ethercat_driver_ros2 ethercat_interface ethercat_msgs"
```

## 5. Build

```sh
cd ~/bar_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-up-to bar_bringup_lite
```

Expected: 11 packages built, with deprecation warnings from the
vcs-imported `mujoco_ros2_control` (`HardwareInfo::on_init` migration,
`get_value()` deprecation) but no errors.

## 6. Source and sanity-check

```sh
source ~/bar_ws/install/setup.bash
ros2 pkg list | grep ^bar_       # expect 11 entries
ros2 control list_hardware_interfaces 2>/dev/null \
    || echo "(no controller_manager running yet — expected)"
```

The 11 packages should be:

```
bar_bringup_lite
bar_bringup_prime
bar_common
bar_controllers
bar_description_lite
bar_description_prime
bar_hw_robstride
bar_hw_sito
bar_hw_socketcan
bar_msgs
bar_policy
```

## Next

You're ready to run the [bar_ros2 101 walkthrough](lite_101.md) — view the
robot in RViz, run a mock bringup, then run the same controllers against
MuJoCo physics.