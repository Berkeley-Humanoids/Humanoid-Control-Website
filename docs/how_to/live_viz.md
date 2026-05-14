---
title: Live-visualize the robot
---

# Live-visualize the robot

Two interchangeable viewers ride on `/joint_states` + `/robot_description`
and render the live kinematic chain. Pick whichever fits your
workflow; both can run simultaneously.

| | `rerun_viz` | `viser_viz` |
|---|---|---|
| Viewer | Native rerun window (auto-opens) | Browser at `http://<host>:8080` |
| Best for | Local desktop; timeline scrubbing; replay-style debugging | Headless robot machine; share over SSH tunnel; URL-shareable |
| URDF parser | `rerun.urdf.UrdfTree` (bundled with `rerun-sdk`) | `yourdfpy.URDF` |
| Pip dep | `rerun-sdk` | `viser`, `yourdfpy`, `scipy>=1.13` |

## Install the pip deps

Neither viewer's pip package is in rosdep on Jazzy, so install once
into the user environment:

```bash
# rerun
pip install --user --break-system-packages rerun-sdk

# viser (the scipy floor avoids a numpy-2 binary-compat conflict with rerun)
pip install --user --break-system-packages viser yourdfpy 'scipy>=1.13'
```

On Ubuntu 24.04 `--break-system-packages` is required because the
distro python is externally managed. If that bothers you, use a
`venv`; the launches inherit `PATH` so a sourced venv works.

## Enable in the launch

Either or both, set with the launch arg(s):

```bash
# MuJoCo + rerun
ros2 launch bar_bringup_lite mujoco.launch.py enable_rerun_viz:=true

# Real Lite + viser
ros2 launch bar_bringup_lite real.launch.py enable_viser_viz:=true

# Both at once
ros2 launch bar_bringup_lite mujoco.launch.py \
    enable_rerun_viz:=true enable_viser_viz:=true
```

The flags spawn the viewer nodes alongside everything else in the
launch. No new terminal needed.

## Run standalone

If you'd rather not modify the launch:

```bash
# Against an already-running stack
ros2 run bar_bringup_lite rerun_viz
ros2 run bar_bringup_lite viser_viz
```

These work against any bringup that publishes `/robot_description`
(latched) and `/joint_states`. They have no opinion on whether the
upstream is silicon, MuJoCo, or `mock_components`.

## Using `viser_viz` over SSH

`viser` serves the viewer on `0.0.0.0:8080` by default — so from any
machine with route to the robot:

```
http://<robot-ip>:8080
```

When you're remote, an SSH tunnel keeps the port off the LAN:

```bash
# On the laptop:
ssh -L 8080:localhost:8080 user@robot
# Now visit http://localhost:8080 in the laptop's browser.
```

The viewer is read-only — there's no command surface in either tool.
For drag-to-command interaction use `rqt_joint_trajectory_controller`
(stock) or `mit_slider_gui` (project).

## Performance notes

| Viewer | Typical CPU on a workstation |
|---|---|
| `rerun_viz` | ~5% per core for 14 joints @ 50 Hz; renders on GPU |
| `viser_viz` | ~10% per core; mostly websocket/JSON overhead |

Both subscribe `/robot_description` with TRANSIENT_LOCAL QoS and
parse the URDF once at startup; runtime cost is just the
per-`/joint_states` callback + a tf update.

## Failure modes

| Symptom | Cause |
|---|---|
| Window opens but robot is blank / collapsed | Mesh `package://` URLs not resolving. Make sure `ros2 launch ...` has `bar_description_lite`'s install on `AMENT_PREFIX_PATH`. |
| `rerun_viz` says `ModuleNotFoundError: No module named 'rerun'` | `pip install --user --break-system-packages rerun-sdk` missing. |
| `viser_viz` complains about `scipy < 1.13` | Numpy-2 binary-compat issue. `pip install --user --break-system-packages 'scipy>=1.13'`. |
| Browser at `:8080` shows "this site can't be reached" | `viser_viz` not spawned (forgot `enable_viser_viz:=true`), or wrong host in the URL. |
| Joints visible in `ros2 topic echo /joint_states` but not moving in viewer | TF buffer staleness — restart the viewer; the URDF subscription may have been late to the latched message. |

## See also

- `rerun_viz` source: [`bar_bringup_lite/scripts/rerun_viz.py`](https://github.com/T-K-233/bar_ros2/blob/main/bar_bringup_lite/scripts/rerun_viz.py)
- `viser_viz` source: [`bar_bringup_lite/scripts/viser_viz.py`](https://github.com/T-K-233/bar_ros2/blob/main/bar_bringup_lite/scripts/viser_viz.py)
- [Reference → Launch args](../reference/launch_args.md) — the
  `enable_rerun_viz` / `enable_viser_viz` entries.
