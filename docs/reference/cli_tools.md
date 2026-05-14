---
title: CLI tools
---

# CLI tools

Standalone executables shipped by `bar_ros2`. All invoked via
`ros2 run <package> <executable>` (no `.py` / extension); each
package's `CMakeLists.txt` installs them under
`<install>/lib/<package>/`.

## Index

| Executable | Package | What it does |
|---|---|---|
| `robstride_ping` | `bar_hw_robstride` | Single-actuator probe (GetDeviceId / OperationStatus). Read-only. |
| `robstride_discover` | `bar_hw_robstride` | Scan a CAN ID range, print every device that replies. Read-only. |
| `mit_slider_gui` | `bar_hw_robstride` | Qt slider window publishing Float64MultiArray to a forward_command_controller. |
| `mode_manager` | `bar_controllers` | The FSM orchestrator. Normally launched by bringup; sometimes useful to start manually. |
| `calibrate_robot` | `bar_bringup_lite` | Sample (min, max) per joint; write `calibration.json` on Ctrl+C. |
| `rerun_viz` | `bar_bringup_lite` | Native rerun viewer subscribed to `/robot_description` + `/joint_states`. |
| `viser_viz` | `bar_bringup_lite` | Browser viewer (default port 8080). Same subscriptions. |

## Per-tool reference

### `robstride_ping`

```bash
ros2 run bar_hw_robstride robstride_ping --iface can0 --id 11
ros2 run bar_hw_robstride robstride_ping --iface can0 --id 11 --read-status
```

| Arg | Default | Description |
|---|---|---|
| `--iface` | `can0` | SocketCAN interface |
| `--id` | `32` | Target Robstride device ID |
| `--timeout-ms` | `500` | How long to wait for the reply |
| `--read-status` | (off) | After GetDeviceId, also Enable → wait for OperationStatus → Disable, for a one-shot pose / fault read |

Read-only when `--read-status` is omitted. With `--read-status`, the
motor is briefly Enabled and Disabled — no MIT operation control, no
commanded motion, but the actuator does transition Enable → Disable
internally.

Used in: [Tutorials → Drive one Robstride](../tutorials/drive_one_robstride.md),
[How-to → Probe CAN bus](../how_to/probe_can_bus.md).

### `robstride_discover`

```bash
ros2 run bar_hw_robstride robstride_discover --iface can0
ros2 run bar_hw_robstride robstride_discover --iface can0 \
    --scan-from 1 --scan-to 127 --per-id-wait-ms 8
```

| Arg | Default | Description |
|---|---|---|
| `--iface` | `can0` | SocketCAN interface |
| `--scan-from` | `1` | Lowest ID to ping |
| `--scan-to` | `32` | Highest ID to ping (inclusive; clamped to 127) |
| `--host-id` | `253` | Host CAN ID used in the GetDeviceId frame |
| `--per-id-wait-ms` | `8` | Gap between successive ping sends |
| `--drain-ms` | `200` | Listen window after the last ping |

Read-only — only `GetDeviceId` is sent. Background drain thread
keeps the RX ring from filling during long scans.

Exit code: `0` if anything answered, `3` if scan completed cleanly
with zero replies. Both are useful in CI.

Used in: [How-to → Probe CAN bus](../how_to/probe_can_bus.md),
[Hardware specs → Bus-bring-up checklist](./hardware_specs.md#bus-bring-up-checklist).

### `mit_slider_gui`

```bash
ros2 run bar_hw_robstride mit_slider_gui
ros2 run bar_hw_robstride mit_slider_gui \
    --joint actuator_1 \
    --command-topic /forward_mit_controller/commands \
    --position-range -3.14 3.14 \
    --kp-range 0 10
```

| Arg | Default | Description |
|---|---|---|
| `--joint` | `actuator_1` | Joint name to read from `/joint_states` |
| `--command-topic` | `/forward_mit_controller/commands` | Float64MultiArray topic to publish to |
| `--state-topic` | `/joint_states` | For the live readout |
| `--position-range` | `-3.14159 3.14159` | Slider range, rad |
| `--velocity-range` | `-1.0 1.0` | rad/s |
| `--effort-range` | `-1.0 1.0` | Nm |
| `--kp-range` | `0.0 10.0` | N·m/rad |
| `--kd-range` | `0.0 1.0` | N·m·s/rad |
| `--default-kp` | `2.0` | Initial slider value |
| `--default-kd` | `0.5` | Initial slider value |

Requires `python_qt_binding` (installed alongside `rqt_reconfigure`).

Used in: [Tutorials → Drive one Robstride](../tutorials/drive_one_robstride.md),
[How-to → mit_slider_gui](../how_to/mit_slider_gui.md).

### `mode_manager`

```bash
ros2 run bar_controllers mode_manager
ros2 run bar_controllers mode_manager --ros-args -p tick_rate_hz:=100
```

| Parameter | Default | Description |
|---|---|---|
| `tick_rate_hz` | `50.0` | Timer rate for `tick()` |
| `controller_manager` | `/controller_manager` | CM namespace |
| `enable_keyboard` | `true` | termios reader on stdin (currently a stub) |
| `joy.damp_button` | `2` | DAMP button index (default = X on Xbox) |
| `joy.quit_button` | `6` | QUIT button index (default = BACK) |
| `joy.load_combo_remote` | `[4, 0]` | LOAD combo paired with R1+A (default = L1+A) |
| `joy.load_combo_locomotion` | `[4, 1]` | LOAD combo paired with R1+B (default = L1+B) |
| `joy.start_combo_remote` | `[5, 0]` | START_REMOTE (default = R1+A) |
| `joy.start_combo_locomotion` | `[5, 1]` | START_LOCOMOTION (default = R1+B) |

Normally launched by `real.launch.py` / `mujoco.launch.py`. Useful
to run standalone when debugging the joy decoder.

Used in: [Concepts → Five-mode FSM](../concepts/five_mode_fsm.md),
[Reference → Controllers](./controllers.md#mode_manager-executable).

### `calibrate_robot`

```bash
ros2 run bar_bringup_lite calibrate_robot --output ./calibration.json
ros2 run bar_bringup_lite calibrate_robot \
    --output ./calibration.json --sweep-threshold 0.3
```

| Arg | Default | Description |
|---|---|---|
| `--output` | (required) | Path to write the resulting JSON |
| `--sweep-threshold` | `0.5` | Min sweep (rad) below which the prior `homing_offset` is preserved |

Normally launched by `calibrate.launch.py` (which sets `--output`
from a launch arg and brings up the rest of the stack). Standalone
invocation is useful if you already have `real.launch.py` running
with `calibration_file:=''`.

Used in: [How-to → Calibrate the zero pose](../how_to/calibrate_zero_pose.md).

### `rerun_viz`

```bash
ros2 run bar_bringup_lite rerun_viz
```

No CLI args today — reads `/robot_description` (latched) once,
subscribes to `/joint_states`, opens the rerun native window.

Requires `pip install rerun-sdk`. Used in:
[How-to → Live viz](../how_to/live_viz.md).

### `viser_viz`

```bash
ros2 run bar_bringup_lite viser_viz
```

Browser viewer at `http://0.0.0.0:8080`. Same subscriptions.

Requires `pip install viser yourdfpy 'scipy>=1.13'`.

## Adding a new CLI tool

For a tool that ships from one of the existing packages:

1. Drop the source in `<package>/scripts/<name>.py` (Python) or
   `<package>/src/<name>.cpp` (C++).
2. In the package's `CMakeLists.txt`, install it under
   `lib/${PROJECT_NAME}` *without* the `.py` extension so
   `ros2 run` finds it:
   ```cmake
   install(
     PROGRAMS scripts/<name>.py
     DESTINATION lib/${PROJECT_NAME}
     RENAME <name>
   )
   ```
   For C++ add the executable target and install it normally — the
   `install(TARGETS ... RUNTIME DESTINATION ...)` lines.
3. Rebuild with `colcon build --packages-select <package> --symlink-install`.
4. Verify with `ros2 pkg executables <package>`.

The `--symlink-install` flag means Python scripts edit-loop without
rebuilding — useful while iterating.
