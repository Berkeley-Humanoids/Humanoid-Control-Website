---
id: use_pixi_tasks
title: Workspace shortcuts with pixi
sidebar_label: Workspace shortcuts (pixi)
---

# Workspace shortcuts with pixi

The rest of this site documents commands in canonical `ros2 launch …` /
`ros2 run …` form. Those work everywhere — Jetson, workstation, CI.

The workspace also ships a thin **alias layer** in
`bar_ws/pixi.toml` so you can shorten the most common command lines
to `pixi run <name>`. This page documents that layer end-to-end:
what each alias maps to, when to reach for it, and how to add your
own.

`pixi.toml` lives at the **workspace level** (`bar_ws/pixi.toml`),
*not* inside `bar_ros2` or `pianist_ros2`. That's intentional — the
file pins ROS 2 Jazzy, the colcon toolchain, every Python dep, and
the activation script that auto-sources `install/setup.bash`. Those
are workspace concerns; both `bar_ros2` and `pianist_ros2` consume them.

:::tip[Why have aliases at all]
A single `pixi run launch-mujoco` is shorter than
`ros2 launch bar_bringup_lite mujoco.launch.py`, but the bigger win
is that **every alias runs inside the pixi-managed environment** —
ROS 2 Jazzy, the colcon overlay, the visualiser PyPI deps, and the
right `RCUTILS_CONSOLE_OUTPUT_FORMAT` are all sourced automatically.
Calling `pixi run …` from a vanilla terminal works without an
explicit `pixi shell` first.
:::

## Build / setup aliases

| Alias | Equivalent | Why |
|---|---|---|
| `pixi install` | (the pixi install itself) | Solve and materialise the conda + PyPI env into `bar_ws/.pixi/`. Run once per clone and after every `pixi.toml` change. |
| `pixi shell` | (the pixi shell itself) | Drop into an interactive shell with the env active. Equivalent to `source install/setup.bash` over a sourced ROS 2 Jazzy install. |
| `pixi run setup` | `vcs import --input src/bar_ros2/bar.repos src` | Clone the third-party `mujoco_*` + `ethercat_driver_ros2` sources listed in `bar.repos` into `src/`. |
| `pixi run build` | `colcon build --symlink-install --packages-skip-regex 'ethercat.*\|bar_bringup_prime'` | Build the Lite path (skips the EtherCAT-linked Prime lane that has no conda recipe). |
| `pixi run build-all` | `colcon build --symlink-install` | Same, but includes `bar_bringup_prime` and `ethercat_driver_ros2`. Requires `libethercat` installed on the host. |
| `pixi run build-pkg <name>` | `colcon build --symlink-install --packages-select <name>` | Targeted rebuild of one package — fastest edit-loop while iterating. |
| `pixi run test` | `colcon test --packages-skip-regex 'ethercat.*\|bar_bringup_prime\|mujoco_.*' --ctest-args -LE linter --event-handlers console_cohesion-` | Run BAR-owned tests; skips the vendored `mujoco_*` packages and the CMake-registered linters (which RoboStack ships at newer versions than apt-jazzy, so they'd diverge from the industrial_ci-on-bar_ros2 source of truth). |
| `pixi run test-lint` | Same as `test`, but keeps the linters. | Use when you specifically want to see uncrustify / cpplint output locally. |
| `pixi run test-results` | `colcon test-result --verbose` | Print the per-package test summary after `pixi run test`. |
| `pixi run clean` | `rm -rf build install log` | Wipe the colcon overlay (leaves the source tree and `.pixi/` env alone). Handy after a package rename. |

## Launch aliases — bar_ros2

Each alias just wraps a `ros2 launch <pkg> <file>` invocation; any
extra arguments after the alias are forwarded unchanged.

| Alias | Equivalent | Side |
|---|---|---|
| `pixi run view` | `ros2 launch bar_bringup_lite view_lite.launch.py` | dev — URDF inspector |
| `pixi run launch-mujoco` | `ros2 launch bar_bringup_lite mujoco.launch.py` | dev — full Lite controller stack in MuJoCo |
| `pixi run launch-real` | `ros2 launch bar_bringup_lite real.launch.py` | robot — real-hardware Lite bringup |
| `pixi run launch-viz` | `ros2 launch bar_bringup_lite viz.launch.py` | host — live URDF + joint-state viewer (`viewer:=viser\|rerun`) |
| `pixi run calibrate` | `ros2 launch bar_bringup_lite calibrate.launch.py` | dev — calibration bringup; writes `calibration.yaml` on Ctrl+C |
| `pixi run launch-policy` | `ros2 launch bar_policy lite_policy.launch.py` | robot — runs `prepare` (resolve ONNX, motion → `.mcap`) then loads the in-process `rl_policy_controller`. Pass `checkpoint_file:=` or `wandb_run_path:=`. |
| `pixi run launch-policy-tracking` | `… lite_policy.launch.py` | robot — pass-through alias (back-compat shortcut) |

### Per-tool / CLI aliases

| Alias | Equivalent |
|---|---|
| `pixi run bar …` | `bar …` (the `bar_cli` console script) |
| `pixi run robstride-ping` | `ros2 run bar_robstride robstride_ping` |
| `pixi run robstride-discover` | `ros2 run bar_robstride robstride_discover` |
| `pixi run mit-slider-gui` | `ros2 run bar_robstride mit_slider_gui` |
| `pixi run rerun-viz` | `ros2 run bar_bringup_lite rerun_viz` |
| `pixi run viser-viz` | `ros2 run bar_bringup_lite viser_viz` |

## Launch aliases — pianist_ros2

Piano-task aliases wrap launches that live in the sibling
`pianist_ros2` repo (the alias still lives at the workspace level —
`pianist_ros2` only ships the launches and Python entry points).

| Alias | Equivalent | Side |
|---|---|---|
| `pixi run launch-mujoco-piano` | `ros2 launch pianist_bringup mujoco.launch.py` | dev — composes Lite + piano scene in MuJoCo |
| `pixi run launch-policy-piano` | `ros2 launch pianist_policy piano_policy.launch.py` | robot — runs `prepare` (song → key-state `.mcap`) then loads the in-process `rl_policy_controller`. Pass `checkpoint_file:=` or `wandb_run_path:=`. |

The USB-MIDI driver launch doesn't have a dedicated alias — invoke it
as `ros2 launch pianist_policy midi_keyboard_driver.launch.py` (or
add an alias yourself, see below).

## Forwarding arguments

`pixi run <alias> arg1 arg2 …` forwards the trailing args to the
underlying command verbatim, so launch-file overrides work the same
way they do under raw `ros2 launch`:

```sh
pixi run launch-real enable_gamepad:=false
pixi run launch-real joy_dev:=/dev/input/js1
pixi run launch-viz  viewer:=rerun
pixi run launch-policy checkpoint_file:=$HOME/model.onnx
pixi run launch-policy-piano wandb_run_path:=entity/project/run-id
```

## Adding a new alias

Edit `bar_ws/pixi.toml`'s `[tasks]` block — that's the only file you
need to touch:

```toml
[tasks]
my-thing = "ros2 launch my_pkg my_launch.py"
```

Then `pixi run my-thing` works immediately; no rebuild needed.

If the alias should live next to the launch file conceptually
(e.g. it's a piano-specific helper), the convention today is to
still register it at the workspace level — `bar_ros2` and
`pianist_ros2` are pure ROS 2 source trees and don't try to expose
a workspace-shell-shortcut layer of their own.

## Tradeoffs vs. plain `ros2 launch`

When to use the aliases:

- One-off interactive bringups where you'll type the command often.
- Operator runbooks — `pixi run launch-real` reads more cleanly
  than the full launch path.
- CI scripts that need the pixi-managed env (the alias inherits it
  automatically, no `pixi shell` wrapping needed).

When to reach for plain `ros2 launch …`:

- Inside a sourced `pixi shell` — the alias adds nothing here, and
  the canonical form is what you'll see in launch-file docstrings
  and in this site.
- When porting commands into another shell, an SSH cheatsheet, or a
  service unit on a machine that doesn't have pixi installed.
- When the surface you're documenting is the launch file itself
  (the alias is a workspace-level shortcut, not a launch feature).
