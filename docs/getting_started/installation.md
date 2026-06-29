# Installation

There are two ways to get BAR onto your machine:

- **Install the prebuilt packages (recommended)** — pull the `ros-jazzy-bar-*`
  conda packages straight from the [`bar-robotics`](https://prefix.dev/channels/bar-robotics)
  channel. No clone, no `colcon`, no compiler — ~2 minutes. Best for running the
  control stack, deploying to a robot or Jetson, or building your own packages on
  top of `bar_msgs` / `bar_controllers`.
- **Build from source** — clone the repos into a pixi workspace and `colcon
  build`. For contributors who modify `bar_ros2`, and for the parts not yet in
  the channel (MuJoCo sim, the piano task, EtherCAT / Prime).

Both use [pixi](https://pixi.sh); neither needs a system-wide `ros-jazzy-desktop`
apt install. The same lockfile / channel reproduces the exact same versions on
every developer machine and on the Jetson.

## System requirements

| Item | Required | Reason |
|---|---|---|
| 64-bit Linux | yes | BAR targets `linux-64` / `linux-aarch64`. macOS and Windows are not supported (SocketCAN + PREEMPT_RT are Linux-only). |
| pixi ≥ 0.30 | yes | manages every other dependency |
| Display server | for sim | `mujoco_sim` opens a GLFW window (source build only, today) |
| PREEMPT_RT kernel | recommended | hard real-time guarantees on real hardware |

We deliberately **do not** require Ubuntu 24.04 or a system-wide
`ros-jazzy-desktop` install. pixi ships ROS 2 Jazzy via the
[RoboStack](https://robostack.github.io) conda channel, isolated inside the
project's `.pixi/`, so a fresh Ubuntu 22.04 / Debian / Fedora host runs the same
stack as a Jazzy-on-24.04 machine.

:::warning[Don't layer pixi over an apt ROS install]
RoboStack and apt-installed ROS share library names but resolve them against
different toolchains. Activate one or the other at a time — never
`source /opt/ros/jazzy/setup.bash` and `pixi shell` together. If you already
have apt ROS on the host, that's fine for other projects; just don't source it
from this workspace's shells.
:::

## Install pixi

Both paths need pixi:

```sh
curl -fsSL https://pixi.sh/install.sh | bash
```

The installer drops a single binary at `~/.pixi/bin/pixi` and adds it to your
shell rc. Restart your shell (or `source ~/.bashrc`) so `pixi` resolves.

## Install the prebuilt packages (recommended)

The BAR packages are published as conda packages on the
[`bar-robotics`](https://prefix.dev/channels/bar-robotics) channel and rebuilt by
the buildfarm on every release. You consume them like any other dependency.

### 1. Create a project and add the channel

```sh
pixi init bar-app
cd bar-app
```

Open `bar-app/pixi.toml` and set the channels + the package(s) you want:

```toml
[workspace]
name = "bar-app"
channels = [
  "https://prefix.dev/bar-robotics",
  "https://prefix.dev/robostack-jazzy",
  "https://prefix.dev/conda-forge",
]
platforms = ["linux-64", "linux-aarch64"]

[dependencies]
# ROS 2 CLI + launch + runtime (ros2 launch / run / pkg). The bar packages
# declare their library deps but not the CLI tooling, so pull a ROS base
# yourself. Use ros-jazzy-desktop instead if you want the RViz-based
# `view` / `viz` launches.
ros-jazzy-ros-base = "*"
# The whole Lite bringup: bar_controllers (ONNX-enabled), bar_msgs,
# lite_description, bar_robstride, bar_socketcan, bar_common, bar_policy.
ros-jazzy-bar-bringup-lite = "*"
# Optional: the `bar` diagnostic CLI (run via `ros2 run bar_cli bar ...`).
ros-jazzy-bar-cli = "*"
```

`bar-robotics` is listed **first** so `ros-jazzy-bar-*` resolves from there, with
RoboStack + conda-forge underneath for the ROS core and native libs. Add only
the packages you need — e.g. `ros-jazzy-bar-msgs` if you just want the message
definitions, or `ros-jazzy-bar-controllers` to build a node against the
controller interfaces. The full set is on the
[Packages reference](../reference/packages.md).

:::note[Pull a ROS base alongside the bar packages]
`ros-jazzy-bar-bringup-lite` pulls its own library dependencies, but **not** the
`ros2 launch` / `ros2 run` / `ros2 pkg` command-line tooling — those live in
`ros-jazzy-ros-base` (or `ros-jazzy-desktop`). Without a ROS base, `ros2 launch`
fails with `invalid choice: 'launch'`. The from-source workspace gets this from
`ros-jazzy-desktop`; a prebuilt project adds it explicitly, as above.
:::

### 2. Resolve and run

```sh
pixi install
pixi run ros2 launch bar_bringup_lite real.launch.py
```

`pixi install` downloads the prebuilt `ros-jazzy-bar-*` binaries plus the
RoboStack ROS core — no build step. Everything the packages ship (launch files,
URDFs, meshes, controller YAMLs, console executables) lands on the ament index,
so `ros2 launch …` / `ros2 run …` work inside `pixi shell` (or via
`pixi run …`). The `bar` diagnostic CLI is a package executable — run it as
`ros2 run bar_cli bar …`.

```sh
pixi shell
ros2 pkg list | grep '^bar_'                              # the bar_* packages you pulled in
ros2 launch bar_bringup_lite real.launch.py --show-args   # dry-parse the launch (no hardware)
ros2 run bar_cli bar bus discover --iface can0 --scan-to 32   # read-only CAN scan, e.g.
```

:::note[What the channel ships today]
`bar-robotics` carries the **11 `ros-jazzy-bar-*` packages** for both `linux-64`
and `linux-aarch64` (Jetson). That covers the full control stack and the
real-hardware **Lite** bringup (`real.launch.py`). Not yet published: the MuJoCo
simulation deps (`mujoco_*`), the piano task (`pianist_*`), and the EtherCAT /
**Prime** packages — for those, use **Build from source** below. They land in
the channel as the buildfarm expands.
:::

:::tip[Optional extras]
Learned policies and the live visualizers pull a few PyPI-only tools. Add them
when you need them:

```sh
# policy prepare (resolve ONNX checkpoint, fetch W&B / LeRobot, write .mcap)
pixi add --pypi onnxruntime huggingface-hub pyarrow wandb
# live viz
pixi add --pypi rerun-sdk viser yourdfpy "scipy>=1.13"
```
:::

## Build from source

For contributors who modify `bar_ros2`, or to get the packages not yet in the
channel (MuJoCo sim, piano task, EtherCAT / Prime). This builds everything with
`colcon` inside the same pixi-managed environment.

### 1. Clone the workspace and sources

`bar_ws` is a thin, **config-only** repo (`bar-ros2-project`): it tracks the pixi
environment and the workspace tasks, and gitignores `src/`. The first-party code
lives in separate repos that you clone into `src/` yourself (third-party deps are
pulled later, in step 3).

```sh
# the config-only workspace
git clone https://github.com/T-K-233/bar-ros2-project.git bar_ws
cd bar_ws

# first-party sources into src/ (gitignored by bar_ws)
git clone https://github.com/T-K-233/bar_ros2.git      src/bar_ros2
git clone https://github.com/T-K-233/pianist_ros2.git  src/pianist_ros2   # optional: piano task
```

`src/bar_ros2` is the package monorepo (required); `src/pianist_ros2` is the
optional piano-task sibling — skip it if you don't need piano. Don't hand-clone
the `mujoco_*` / `ethercat_driver_ros2` dependencies; `vcs import` pulls those in
step 3.

### 2. Resolve the environment

```sh
pixi install
```

First run takes ~3–5 minutes (downloads `ros-jazzy-desktop` and the control stack
from RoboStack, plus the PyPI deps for the visualisers and the policy runner).
Subsequent runs are instant — pixi reads the committed `pixi.lock` for an exact,
reproducible solve.

### 3. Pull third-party sources

```sh
vcs import --input src/bar_ros2/bar.repos src
```

This brings in the three `mujoco_*` packages and `ethercat_driver_ros2` under
`src/`. No `rosdep init` / `update` / `install` — the pixi env already provides
every dep declared in any package.xml across this workspace, so rosdep has
nothing to add. If a future vcs-imported package needs a dep we don't have, the
colcon build fails with a clear CMake error — add the dep to `pixi.toml`'s
`[dependencies]` and rerun.

:::warning[Optional: skip the EtherCAT path]
`ethercat_driver_ros2` links `libethercat`, which has no conda recipe. The
default build below skips `ethercat.*` and `bar_bringup_prime` so Lite bringup
works on any host. To enable Prime, install the IgH EtherLAB master from source
on the host, then drop the `--packages-skip-regex` filter.
:::

### 4. Enter the env and build

```sh
pixi shell
colcon build --symlink-install --packages-skip-regex 'ethercat.*|bar_bringup_prime'
```

`pixi shell` sources the conda env and `bar_ws/install/setup.bash` once it
exists, so `ros2`, `colcon`, and every console script land on `PATH`. The build
covers the Lite path (every BAR + Pianist package plus the three `mujoco_*`
deps). `--symlink-install` means edits to launch / config / Python files are
picked up without rebuilding. After the first successful build the install
overlay is on `AMENT_PREFIX_PATH` automatically — pixi's `[activation]` block
re-sources `install/setup.bash` whenever you enter `pixi shell`.

### 5. Sanity-check

```sh
ros2 pkg list | grep '^bar_'        # 12 entries from bar_ros2
ros2 pkg list | grep '^pianist_'    # 4 entries from pianist_ros2
ros2 control list_hardware_interfaces 2>/dev/null \
    || echo "(no controller_manager running yet — expected)"
```

The 11 `bar_ros2` packages (Lite's `lite_description` comes separately, via `bar.repos`):

```
bar_bringup_lite
bar_bringup_prime
bar_cli
bar_common
bar_controllers
bar_robstride
bar_sito
bar_socketcan
bar_msgs
bar_policy
```

The 4 `pianist_ros2` packages (present only if you cloned the piano-task sibling
repo into `src/pianist_ros2`):

```
pianist_assets
pianist_bringup
pianist_msgs
pianist_policy
```

See [Packages reference](../reference/packages.md) for what each one ships and
how the two repos split responsibilities.

## Next

You're ready to run the [Lite 101 walkthrough](lite_101.md) — view the robot in
RViz, run a mock bringup, then run the same controllers against MuJoCo physics.
(The MuJoCo steps need the source build above, until `mujoco_*` lands in the
channel.)

If you'd like to know what the `pixi run launch-mujoco` / `pixi run build`
shortcuts you'll see in some scripts and READMEs actually do, jump to
[How-to → Workspace shortcuts with pixi](../how_to/use_pixi_tasks.md).
