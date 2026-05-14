---
title: Topics & services
---

# Topics & services

Index of the ROS topics and services that `bar_ros2` publishes,
subscribes, or serves. Use this page to find "who publishes X" or
"what topic carries Y".

## Topics

### Always-on (any bringup)

| Topic | Type | QoS | Publisher | Notes |
|---|---|---|---|---|
| `/joint_states` | `sensor_msgs/JointState` | RELIABLE depth 10 | `joint_state_broadcaster` | Position/velocity/effort in joint frame (post-calibration). Updates at `controller_manager.update_rate`. |
| `/robot_description` | `std_msgs/String` | RELIABLE TRANSIENT_LOCAL depth 1 | `robot_state_publisher` | URDF XML. Latched — subscribers can join any time. |
| `/tf`, `/tf_static` | `tf2_msgs/TFMessage` | RELIABLE | `robot_state_publisher` | Kinematic chain from `/joint_states`. |
| `/clock` | `rosgraph_msgs/Clock` | RELIABLE | `mujoco_sim` (sim only) | Sim-time on the MuJoCo path. Every other node consumes when `use_sim_time:=true`. |

### Bringup-dependent

| Topic | Type | QoS | Publisher | When present |
|---|---|---|---|---|
| `/control_mode` | `bar_msgs/ControlMode` | RELIABLE depth 10 | `mode_manager` | When `enable_mode_manager:=true` (default for `real.launch.py` / `mujoco.launch.py`). |
| `/safety_status` | `bar_msgs/SafetyStatus` | RELIABLE TRANSIENT_LOCAL depth 1 | every hardware plugin | Per-bus (`bar_hw_robstride/can0`, `bar_hw_robstride/can1` for Lite). Published only on change. |
| `/standby_controller/state` | `bar_msgs/StandbyState` | RELIABLE TRANSIENT_LOCAL depth 1 | `bar/StandbyController` (when active) | Carries `is_finished` — the gate for `START_*` intents. |
| `/joy` | `sensor_msgs/Joy` | SENSOR_DATA | `joy_node` | When `enable_gamepad:=true`. |

### Active-controller-dependent

| Topic | Type | QoS | Direction | When |
|---|---|---|---|---|
| `/remote_policy_controller/command` | `bar_msgs/MITAction` | RELIABLE depth 4 | subscribed by `RemotePolicyController` | When `RemotePolicyController` is active. Published by `bar_policy/remote_policy_runner`. |
| `/imu/data` | `sensor_msgs/Imu` | SENSOR_DATA | subscribed by `RLPolicyController` and `bar_policy` | When the IMU node is running. Not currently auto-launched. |
| `/forward_mit_controller/commands` | `std_msgs/Float64MultiArray` | RELIABLE depth 10 | subscribed by upstream `forward_command_controller/MultiInterfaceForwardCommandController` | Used by `mit_slider_gui`. |

### `/parameter_events` and friends

Every node (controllers, mode_manager, plugins) publishes the
standard ROS infrastructure topics:
- `/parameter_events`, `/rosout`
- `~/get_parameters`, `~/set_parameters`, etc. (per node)

These are conventional ROS — not specific to `bar_ros2`. Mentioned
here so `ros2 topic list` output isn't confusing.

## Services

### controller_manager-side (under `/controller_manager`)

Standard `controller_manager` services. Useful ones:

| Service | Type | Purpose |
|---|---|---|
| `/controller_manager/list_controllers` | `controller_manager_msgs/ListControllers` | What's loaded, active state per controller |
| `/controller_manager/list_hardware_components` | `controller_manager_msgs/ListHardwareComponents` | Which `<ros2_control>` blocks are active |
| `/controller_manager/load_controller` | `controller_manager_msgs/LoadController` | Backing for `ros2 control load_controller` |
| `/controller_manager/switch_controller` | `controller_manager_msgs/SwitchController` | Backing for `ros2 control switch_controllers` |
| `/controller_manager/configure_controller` | `controller_manager_msgs/ConfigureController` | Force `on_configure` |

`mode_manager` is a client of `/controller_manager/switch_controller`
(async, STRICT). You can call it directly from `ros2 control` for
operator-driven debug — see
[How-to → Switch without the FSM](../how_to/switch_controllers_manually.md).

### Per-node services (parameter handling)

Every node hosts the standard rclcpp parameter services:
- `~/get_parameters`, `~/set_parameters`, `~/list_parameters`, etc.

`rqt_reconfigure` is a generic frontend for these.

## QoS reference

Used in the tables above:

| QoS profile | Reliability | Durability | History | When |
|---|---|---|---|---|
| `RELIABLE` (default) | RELIABLE | VOLATILE | KEEP_LAST 10 | Most topics |
| `SENSOR_DATA` | BEST_EFFORT | VOLATILE | KEEP_LAST 5 | High-rate sensors — IMU, joy |
| `TRANSIENT_LOCAL` | RELIABLE | TRANSIENT_LOCAL | KEEP_LAST 1 | Latched — late subscribers see the most-recent value (URDF, SafetyStatus, StandbyState) |

If a publisher's QoS doesn't match a subscriber's, ROS may silently
drop messages. The TRANSIENT_LOCAL combo is the most common
mismatch source — subscribers must also request TRANSIENT_LOCAL
durability to receive the latched value.

## Inspecting at runtime

```bash
# What's published right now?
ros2 topic list

# Who's publishing X?
ros2 topic info /control_mode --verbose

# What's the QoS?
ros2 topic info /safety_status --verbose

# Recent rate
ros2 topic hz /joint_states

# What service does X expose?
ros2 service list | grep mode_manager
ros2 service info /controller_manager/switch_controller
```

## See also

- [Reference → Messages](./messages.md) — full field schemas for the
  custom `bar_msgs` types.
- [Reference → Quick reference](./quick_reference.md) — common
  `ros2 topic echo` / `ros2 topic hz` invocations.
- [Concepts → Safety pipeline](../concepts/safety_pipeline.md) — what
  triggers a `/safety_status` publish.
