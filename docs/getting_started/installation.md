# Installation

Get from a fresh clone to a built `bar_ws` in ~10 minutes. Everything is
managed by [pixi](https://pixi.sh) — one tool resolves ROS 2 Jazzy, the
build toolchain, the Python deps, and the colcon side, and pins exact
versions across machines via a committed `pixi.lock`.

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

## 2. Clone the workspace

```sh
git clone --recurse-submodules https://github.com/T-K-233/BAR-Lowlevel-System-WS.git
cd BAR-Lowlevel-System-WS/bar_ws
```

`--recurse-submodules` is what brings in `src/bar_ros2`. If you forgot it
on the initial clone: `git submodule update --init --recursive`.

## 3. Resolve the environment

```sh
pixi install
```

First run takes ~3–5 minutes (downloads `ros-jazzy-desktop` and the
control stack from RoboStack, plus the PyPI deps for the visualisers and
the policy runner). Subsequent runs are instant — pixi reads the
committed `pixi.lock` for an exact, reproducible solve.

## 4. Pull third-party sources and rosdeps

```sh
pixi run setup
```

This wraps two steps inside the pinned env:

1. `vcs import < src/bar_ros2/bar.repos src` — clones the three
   `mujoco_*` packages plus `ethercat_driver_ros2` into `src/`.
2. `rosdep install --from-paths src --ignore-src -y` with the EtherCAT
   keys skipped (see below).

:::warning[Optional: skip the EtherCAT path]
`ethercat_driver_ros2` links `libethercat`, which has no conda recipe.
The `setup` task `--skip-keys`'s it; the `build` task `--packages-skip-regex`'s
`ethercat.*|bar_bringup_prime` for the same reason. Lite bringup does not
depend on EtherCAT, so you're done. To enable Prime, install IgH EtherLAB
master from source on the host, then `pixi run build-all` instead of
`pixi run build`.
:::

## 5. Build

```sh
pixi run build
```

Builds the Lite path (every BAR package plus the three `mujoco_*` deps).
Expected: 11 BAR packages + 3 mujoco vendored packages, with deprecation
warnings from the upstream `mujoco_ros2_control`
(`HardwareInfo::on_init` migration, `get_value()` deprecation) but no
errors.

## 6. Sanity-check

```sh
pixi run -- ros2 pkg list | grep '^bar_'        # expect 12 entries
pixi run -- ros2 control list_hardware_interfaces 2>/dev/null \
    || echo "(no controller_manager running yet — expected)"
```

The 12 BAR packages should be:

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
bar_piano
bar_policy
```

You can also `pixi shell` to drop into an interactive shell with
`install/setup.bash` already sourced — that's the same environment every
`pixi run …` task runs inside.

## What pixi gives you

The `pixi.toml` at `bar_ws/pixi.toml` defines every named task:

| Task | What it does |
|---|---|
| `pixi run setup` | `vcs import` + `rosdep install`. Re-run after a `bar.repos` change. |
| `pixi run build` | colcon build, Lite path (skips `ethercat_*` + `bar_bringup_prime`). |
| `pixi run build-all` | colcon build including the EtherCAT lane. Requires `libethercat` on the host. |
| `pixi run build-pkg <name>` | targeted rebuild of one package. |
| `pixi run test` | colcon test, BAR-owned packages only. |
| `pixi run test-results` | colcon test-result --verbose. |
| `pixi run sim` | Lite MuJoCo bringup (alias: `launch-mujoco`). |
| `pixi run sim-piano` | same with the portable piano scene (alias: `launch-mujoco-piano`). |
| `pixi run real` | Lite real-hardware bringup (alias: `launch-real`). |
| `pixi run view` | `view_lite` RViz inspection. |
| `pixi run calibrate` | calibration bringup (Ctrl+C writes `calibration.yaml`). |
| `pixi run setup-realtime` | grant RT scheduling capability to `ros2_control_node`. Once per machine, see below. |
| `pixi run clean` | wipe `build/`, `install/`, `log/`. |

## 7. Real-time scheduling setup (recommended)

By default the controller_manager logs `Could not enable FIFO RT
scheduling policy: Operation not permitted` on every launch — it tries
to bring its 50 Hz tick onto `SCHED_FIFO` priority 50 but lacks the
capability. The result is best-effort scheduling on `SCHED_OTHER`,
which is fine for sim but introduces jitter on real Robstride
hardware.

```sh
pixi run setup-realtime
```

This one-time setup:

1. Runs `setcap cap_sys_nice+ep` on the `ros2_control_node` binary so
   it can call `sched_setscheduler(SCHED_FIFO, ...)` without being
   root.
2. Writes `/etc/security/limits.d/99-bar-realtime.conf` granting
   `rtprio 99` + `memlock unlimited` to all users. Log out + back in
   for the new limits to take effect for your shell.
3. Writes `/etc/sysctl.d/99-bar-realtime.conf` setting
   `kernel.sched_rt_runtime_us = -1` so RT tasks aren't throttled to
   95 % of a 1-second period (the default would starve a hot 50 Hz
   loop).

After running it, verify with:

```sh
pixi run real
# expect NO "Could not enable FIFO RT scheduling policy" log line.

ps -eLo pid,tid,class,rtprio,comm | grep ros2_control_node
# expect: class FF (FIFO), rtprio 50.
```

:::info[PREEMPT_RT kernel]
For hard real-time guarantees you also want a PREEMPT_RT kernel. On
Ubuntu 24.04 the simplest path is the `linux-generic-rt` package from
the `ppa:rt-kernel-team/ppa` PPA (or build from
`kernel.org/pub/linux/kernel/projects/rt/`). The `setup-realtime` task
above warns if it doesn't detect `PREEMPT_RT` in `uname -v` but does
not install the kernel — that's a deliberate one-time decision the
operator makes per machine.
:::

## Next

You're ready to run the [bar_ros2 101 walkthrough](lite_101.md) — view the
robot in RViz, run a mock bringup, then run the same controllers against
MuJoCo physics.
