# Installation

Get from a fresh clone to a built `bar_ws` in ~10 minutes. The
environment (ROS 2 Jazzy + colcon + every Python and native dep) is
managed by [pixi](https://pixi.sh) so the same lockfile reproduces the
exact same versions on every developer machine and on the Jetson.

Once the environment is active, every command on the rest of these
docs is plain ROS 2 (`ros2 launch …`, `ros2 run …`, `colcon build`).
The workspace also ships a small set of one-line aliases (`pixi run
launch-mujoco`, `pixi run build`, …) — that alias surface is
documented separately on [How-to → Workspace shortcuts with
pixi](../how_to/use_pixi_tasks.md).

## System requirements

| Item | Required | Reason |
|---|---|---|
| 64-bit Linux | yes | the workspace targets `linux-64` / `linux-aarch64`. macOS and Windows are not supported (SocketCAN + PREEMPT_RT are Linux-only). |
| pixi ≥ 0.30 | yes | manages every other dependency |
| Display server | for sim | `mujoco_sim` opens a GLFW window |
| PREEMPT_RT kernel | recommended | hard real-time guarantees on real hardware |

We deliberately **do not** require Ubuntu 24.04 or a system-wide
`ros-jazzy-desktop` install. pixi ships ROS 2 Jazzy via the
[RoboStack](https://robostack.github.io) conda channel, isolated inside
`bar_ws/.pixi/`, so a fresh Ubuntu 22.04 / Debian / Fedora host can run
the same workspace as a Jazzy-on-24.04 machine.

:::warning[Don't layer pixi over an apt ROS install]
RoboStack and apt-installed ROS share library names but resolve them
against different toolchains. Activate one or the other at a time — never
`source /opt/ros/jazzy/setup.bash` and `pixi shell` together. If you
already have apt ROS on the host, that's fine for other projects; just
don't source it from this workspace's shells.
:::

## 1. Install pixi

```sh
curl -fsSL https://pixi.sh/install.sh | bash
```

The installer drops a single binary at `~/.pixi/bin/pixi` and adds it to
your shell rc. Restart your shell (or `source ~/.bashrc`) so `pixi`
resolves.

## 2. Clone the workspace and sources

`bar_ws` is a thin, **config-only** repo: it tracks the pixi environment
and the workspace tasks, and gitignores `src/`. The first-party code lives
in separate repos that you clone into `src/` yourself (third-party deps are
pulled later, in step 4).

```sh
# the config-only workspace
git clone https://github.com/T-K-233/bar-ros2-project.git bar_ws
cd bar_ws

# first-party sources into src/ (gitignored by bar_ws)
git clone https://github.com/T-K-233/bar_ros2.git      src/bar_ros2
git clone https://github.com/T-K-233/pianist_ros2.git  src/pianist_ros2   # optional: piano task
```

`src/bar_ros2` is the package monorepo (required); `src/pianist_ros2`
is the optional piano-task sibling — skip it if you don't need piano.
Don't hand-clone the `mujoco_*` / `ethercat_driver_ros2` dependencies;
`vcs import` pulls those in step 4.

## 3. Resolve the environment

```sh
pixi install
```

First run takes ~3–5 minutes (downloads `ros-jazzy-desktop` and the
control stack from RoboStack, plus the PyPI deps for the visualisers and
the policy runner). Subsequent runs are instant — pixi reads the
committed `pixi.lock` for an exact, reproducible solve.

## 4. Pull third-party sources

```sh
vcs import --input src/bar_ros2/bar.repos src
```

This brings in the three `mujoco_*` packages and `ethercat_driver_ros2`
under `src/`. No `rosdep init` / `update` / `install` — the pixi env
already provides every dep declared in any package.xml across this
workspace (eigen, glfw, yaml-cpp, numpy, pytest, pyyaml, click, the
ament-* and ros2-control bits via `ros-jazzy-desktop`), so rosdep has
nothing to add. If a future vcs-imported package needs a dep we don't
have, the colcon build fails with a clear CMake error — add the dep to
`pixi.toml`'s `[dependencies]` and rerun.

:::warning[Optional: skip the EtherCAT path]
`ethercat_driver_ros2` links `libethercat`, which has no conda recipe.
The default build below skips `ethercat.*` and `bar_bringup_prime` so
Lite bringup works on any host. To enable Prime, install the IgH
EtherLAB master from source on the host, then drop the
`--packages-skip-regex` filter.
:::

## 5. Enter the env

Every subsequent step (build, launch, `ros2 …`) needs the pixi-managed
environment active. The simplest way is an interactive shell:

```sh
pixi shell
```

That sources `/opt/ros/jazzy`-equivalent paths from the conda env and
`bar_ws/install/setup.bash` once it exists, so `ros2`, `colcon`, and
every console script land on `PATH`. You stay in that shell for the
rest of the session; the rest of these docs assume you're inside it.

## 6. Build

```sh
colcon build --symlink-install --packages-skip-regex 'ethercat.*|bar_bringup_prime'
```

Builds the Lite path (every BAR + Pianist package plus the three
`mujoco_*` deps). `--symlink-install` means edits to launch / config /
Python files are picked up without rebuilding. Expected: 12 BAR
packages + 4 Pianist packages + 3 mujoco vendored packages, with
deprecation warnings from the upstream `mujoco_ros2_control` but no
errors.

After the first successful build the install overlay is on
`AMENT_PREFIX_PATH` automatically — pixi's `[activation]` block
re-sources `install/setup.bash` whenever you enter `pixi shell`.

## 7. Sanity-check

```sh
ros2 pkg list | grep '^bar_'        # 12 entries from bar_ros2
ros2 pkg list | grep '^pianist_'    # 4 entries from pianist_ros2
ros2 control list_hardware_interfaces 2>/dev/null \
    || echo "(no controller_manager running yet — expected)"
```

The 12 `bar_ros2` packages:

```
bar_bringup_lite
bar_bringup_prime
bar_cli
bar_common
bar_controllers
bar_description_lite
bar_description_prime
bar_robstride
bar_sito
bar_socketcan
bar_msgs
bar_policy
```

The 4 `pianist_ros2` packages (present only if you cloned the
piano-task sibling repo into `src/pianist_ros2` in step 2):

```
pianist_assets
pianist_bringup
pianist_msgs
pianist_policy
```

See [Packages reference](../reference/packages.md) for what each one
ships and how the two repos split responsibilities.

## Next

You're ready to run the [Lite 101 walkthrough](lite_101.md) — view the
robot in RViz, run a mock bringup, then run the same controllers
against MuJoCo physics.

If you'd like to know what the `pixi run launch-mujoco` /
`pixi run build` shortcuts you'll see in some scripts and READMEs
actually do, jump to
[How-to → Workspace shortcuts with pixi](../how_to/use_pixi_tasks.md).
