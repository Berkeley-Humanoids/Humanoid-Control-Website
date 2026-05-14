---
id: quick_reference
title: Quick reference
sidebar_label: Quick reference
---

# Quick reference

Dense, scannable lookup for the most common commands, topics, and
parameters. The cheat sheet you print or pin to a second monitor.
Every link points at the page with the full details.

## Launch invocations

```bash
# Drag joints in RViz — no controllers, no physics
ros2 launch bar_description_lite view_lite.launch.py

# MuJoCo sim — full controller stack, /clock from sim time
ros2 launch bar_bringup_lite mujoco.launch.py
ros2 launch bar_bringup_lite mujoco.launch.py enable_rerun_viz:=true
ros2 launch bar_bringup_lite mujoco.launch.py enable_viser_viz:=true

# Real Lite — both buses, two ros2_control blocks
ros2 launch bar_bringup_lite real.launch.py
ros2 launch bar_bringup_lite real.launch.py \
    can_interface_left:=can0 can_interface_right:=can1 \
    enable_gamepad:=true

# Real Lite, no FSM (raw debug / calibration)
ros2 launch bar_bringup_lite real.launch.py enable_mode_manager:=false

# Calibrate the zero pose
ros2 launch bar_bringup_lite calibrate.launch.py
```

Full surface: [Launch args](./launch_args.md).

## CAN bus setup

```bash
# One-time, after USB-to-CAN adapters plug in
sudo ip link set can0 down 2>/dev/null
sudo ip link set can0 up type can bitrate 1000000
sudo ip link set can1 down 2>/dev/null
sudo ip link set can1 up type can bitrate 1000000

# Check state (look for "UP" and "ERROR-ACTIVE")
ip -d link show can0
ip -d link show can1
```

## Diagnostic CLIs

```bash
# Scan an ID range; read-only, no Enable
ros2 run bar_hw_robstride robstride_discover --iface can0 --scan-to 32
ros2 run bar_hw_robstride robstride_discover --iface can1 --scan-to 32

# One-shot GetDeviceId / OperationStatus probe
ros2 run bar_hw_robstride robstride_ping --iface can0 --id 11

# Per-joint slider window (forward_command_controller frontend)
ros2 run bar_hw_robstride mit_slider_gui

# Live URDF + /joint_states viewers
ros2 run bar_bringup_lite rerun_viz       # native window
ros2 run bar_bringup_lite viser_viz       # browser at :8080
```

## Mode-FSM gamepad bindings (Xbox layout)

| Buttons | Intent | Allowed from | Activates |
|---|---|---|---|
| `X` | DAMP | any state | `damping_controller` |
| `L1 + A` *or* `L1 + B` | LOAD | DAMPING | `standby_controller` |
| `R1 + A` | START_REMOTE | STANDBY (gated on `is_finished`) | `remote_policy_controller` |
| `R1 + B` | START_LOCOMOTION | STANDBY (gated on `is_finished`) | `rl_policy_controller` |
| `BACK` | QUIT | ZERO_TORQUE or DAMPING only | `rclcpp::shutdown()` |

Pair conventionally: `L1+A → R1+A` for remote-policy, `L1+B → R1+B` for
locomotion. Combos are identical functionally; the operator's thumb
just stays on one column. See [Concepts → Five-mode FSM](../concepts/five_mode_fsm.md).

## Manual controller switching (no FSM)

```bash
# ZERO_TORQUE → DAMPING
ros2 control switch_controllers \
    --deactivate zero_torque_controller \
    --activate   damping_controller

# DAMPING → STANDBY (motors will move to piano-ready over ~4 s)
ros2 control switch_controllers \
    --deactivate damping_controller \
    --activate   standby_controller

# Back to safe
ros2 control switch_controllers \
    --deactivate <whatever>_controller \
    --activate   zero_torque_controller
```

Always end a session with `zero_torque_controller` active before
`Ctrl+C`-ing the launch.

## Topics you actually echo

| Topic | Type | Rate | When |
|---|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | 50 Hz | always (controller_manager update_rate) |
| `/control_mode` | `bar_msgs/ControlMode` | 50 Hz | always (mode_manager tick rate) |
| `/safety_status` | `bar_msgs/SafetyStatus` | on-change, latched | per-bus on real hardware; OK frame at boot |
| `/standby_controller/state` | `bar_msgs/StandbyState` | active-only | watch for `is_finished:true` before R1+A |
| `/remote_policy_controller/command` | `bar_msgs/MITAction` | 50 Hz | when `bar_policy/remote_policy_runner` is up |
| `/joy` | `sensor_msgs/Joy` | sensor-rate | when `enable_gamepad:=true` |

## Common one-liners

```bash
# Live controller state
ros2 control list_controllers

# Rate of /joint_states (should be 50 Hz, σ < 1 ms)
ros2 topic hz /joint_states

# Read the current pose (post-calibration, joint frame)
ros2 topic echo --once /joint_states

# Safety status of every active bus
ros2 topic echo --once /safety_status

# Fake an MITAction publish (when remote_policy_controller is active in MuJoCo)
ros2 topic pub --once /remote_policy_controller/command \
    bar_msgs/msg/MITAction "{header: {stamp: now}, joint_names: [...], ...}"
```

## The Lite joint table

14 actuated DOFs across two buses. Order is canonical (see
[Concepts → Frozen schemas](../concepts/frozen_schemas.md)).

| Idx | Joint | CAN id | Bus | Model |
|---|---|---:|---|---|
| 0 | `left_shoulder_pitch`  | 11 | can0 | rs-02 |
| 1 | `left_shoulder_roll`   | 12 | can0 | rs-00 |
| 2 | `left_shoulder_yaw`    | 13 | can0 | rs-00 |
| 3 | `left_elbow_pitch`     | 14 | can0 | rs-00 |
| 4 | `left_wrist_yaw`       | 15 | can0 | rs-05 |
| 5 | `left_wrist_roll`      | 16 | can0 | rs-05 |
| 6 | `left_wrist_pitch`     | 17 | can0 | rs-05 |
| 7 | `right_shoulder_pitch` | 21 | can1 | rs-02 |
| 8 | `right_shoulder_roll`  | 22 | can1 | rs-00 |
| 9 | `right_shoulder_yaw`   | 23 | can1 | rs-00 |
| 10 | `right_elbow_pitch`   | 24 | can1 | rs-00 |
| 11 | `right_wrist_yaw`     | 25 | can1 | rs-05 |
| 12 | `right_wrist_roll`    | 26 | can1 | rs-05 |
| 13 | `right_wrist_pitch`   | 27 | can1 | rs-05 |

Full table (effort / current limits / per-joint K/D) in
[Hardware specs → Joint table](./hardware_specs.md#joint-table).

## MIT-mode command convention

Every plugin (Robstride, Sito, MujocoSystem) computes torque as:

```
τ = K_p · (q_cmd − q) + K_d · (q̇_cmd − q̇) + τ_ff
```

Five command interfaces per joint: `position`, `velocity`, `effort`,
`stiffness`, `damping`. Three state interfaces: `position`, `velocity`,
`effort`. See [Concepts → MIT command surface](../concepts/mit_command_surface.md).

## Frequent failure modes (one-liners)

| Symptom | First thing to check |
|---|---|
| `ENOBUFS` / `Network is down` warnings | Motor power off → frames don't ACK → qdisc fills. Power the motors. |
| `/joint_states` shows exactly 0.0 for every joint | Motors un-Enabled (no power, or Enable frame dropped). Check `/safety_status flags`. |
| Spawner reports `Failed to configure controller` for `rl_policy_controller` | Placeholder `observation_dim=0`. Drop it from the inactive-spawner batch or update the YAML. |
| `mode_manager` rejects `LOAD` from anywhere other than DAMPING | Send DAMP (`X`) first. See FSM table above. |
| `ros2 topic echo /safety_status` reports `flags ≠ 0` | Check [Concepts → Safety pipeline](../concepts/safety_pipeline.md) for the bit definitions. |

Full guidance: [Troubleshooting](./troubleshooting.md).
