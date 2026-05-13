# Packages

The `bar_ros2` repo is a flat collection of 11 packages, organized by which
robot(s) consume them and what role they play.

## At a glance

## Per-package details

### `bar_common`

Header-only POD types and real-time helpers. Every C++ package in the workspace
depends on this.

| Header | Purpose |
|---|---|
| `mit_state.hpp` | `bar::MITState` — canonical observation struct (joint pos/vel/effort, IMU quat in **(w, x, y, z)** order, body-frame gyro/accel, last_action). Code-level schema, not a published topic. |
| `joint_index_map.hpp` | Bidirectional `name ↔ index` map, used to validate incoming `MITAction` joint_names against a controller's claimed order. |
| `rt_utils.hpp` | RT-safe primitives: `monotonic_ns()`, `all_finite(...)`, `clamp(...)`. No allocations. |
| `loaned_interface_helpers.hpp` | `bar::set_cmd(...)` and `bar::get_state(...)` — discard wrappers for Jazzy's `[[nodiscard]] bool set_value()` and `get_optional<T>()` migration. Centralizes the Kilted migration to one file. |

### `bar_msgs`

Custom ROS 2 interfaces. Once a trained policy depends on one, it is **frozen**.

| Message | Used by |
|---|---|
| `MITAction` | `bar_policy` → `RemotePolicyController`. The on-wire action format. |
| `ControlMode` | `mode_manager` → `/control_mode` telemetry. |
| `StandbyState` | `StandbyController` → `/standby_controller/state` (`is_finished` gate for the `START_LOCOMOTION` / `START_REMOTE` intents). |
| `SafetyStatus` | every hardware plugin / controller → `/safety_status`. Plugin-specific bitmask in `flags`. |
| `VLAGoal` | (stub) vision-language-action policy goal description. |

See [Messages reference](messages.md) for full schemas.

### `bar_description_lite` / `bar_description_prime`

URDF / xacro / meshes / `<ros2_control>` blocks.

Layout (Lite shown):

```
bar_description_lite/
├── urdf/
│   ├── lite.urdf.xacro              # top-level, 17 joints
│   └── lite.ros2_control.xacro      # 3-way plugin selector
├── meshes/   *.stl                  # 18 visual meshes
├── mjcf/     lite.xml               # MuJoCo physics model
├── config/   view_lite.rviz         # RViz config
└── launch/   view_lite.launch.py    # standalone visualization
```

The xacro selects between **three hardware backends** via args:

![flowchart LR](/img/diagrams/reference__packages__02.svg)

### `bar_hw_socketcan`

Reusable SocketCAN bus library. Owns the kernel-facing CAN socket lifecycle, a
dedicated I/O thread, and lock-free buffers. Per-actuator-family plugins
(`bar_hw_robstride`, `bar_hw_sito`) consume its synchronous `read_state()` /
`write_command()` API.

**Pattern reference**: mirrors the `soem_ros2` / `cleardrive_ros2` split from
`legged_control2`.

### `bar_hw_robstride` / `bar_hw_sito`

Per-actuator-family `hardware_interface::SystemInterface` plugins.
`bar_hw_robstride` for Lite (and Prime's auxiliary joints if added later);
`bar_hw_sito` for Prime's Sito side.

Both:
- Export the standard **3 state interfaces** (`<joint>/position`, `<joint>/velocity`, `<joint>/effort`).
- Export the **5 MIT-mode command interfaces** (`position`, `velocity`, `effort`, `stiffness`, `damping`).
- Read `can_interface` (system-level) and per-joint `can_id` from URDF params.
- Register via `pluginlib` against `hardware_interface::SystemInterface`.

### `bar_controllers`

Five mode-FSM controllers + the standalone `mode_manager` executable.

| Plugin | State | Source |
|---|---|---|
| `bar/ZeroTorqueController` | startup, safer fault fallback | `zero_torque_controller.cpp` |
| `bar/DampingController` | compliant fail-safe | `damping_controller.cpp` |
| `bar/StandbyController` | pose interpolation + gain ramp | `standby_controller.cpp` |
| `bar/RLPolicyController` | in-process ONNX (locomotion) | `rl_policy_controller.cpp` |
| `bar/RemotePolicyController` | thin executor for `bar_policy` | `remote_policy_controller.cpp` |
| `mode_manager` exe | FSM orchestrator | `mode_manager.cpp` |

See [Controllers reference](controllers.md).

### `bar_policy`

The only ament_python package in the workspace. Runs ONNX policies
out-of-process and publishes `MITAction` over DDS to
`bar::RemotePolicyController`. The `remote_policy_runner` node composes
six subsystems:

| Module | Role |
|---|---|
| `onnx_policy.OnnxPolicyRunner` | Thin `onnxruntime.InferenceSession` wrapper; float32 (1, N) -> (1, M). |
| `policy_metadata.PolicyMetadata` | Typed access to the 13 self-describing fields baked into the ONNX `custom_metadata_map` (joint names, gains, default pose, observation term names, dataset id, ...). |
| `observation_manager.ObservationManager` | Concatenates configured `ObservationTerm` slices into the policy's flat input vector. Owns the reference-provider lifecycle (reset / step). |
| `term_builders` | Registry mapping observation-term names from the ONNX (`joint_pos`, `joint_vel`, `actions`, `imu_*`, `ref_body_pos`, ...) to `ObservationTerm` instances. |
| `reference.tracking.TrackingReferenceProvider` | Loads a LeRobot dataset and serves per-frame teleop targets (body positions / orientations, joint references) on the cadence the manager steps it. |
| `action_decoder.PolicyActionDecoder` + `ActionMapper` | Decode `target = default + scale * action` per action joint, then assemble a full-articulation `MITAction` with undriven joints pinned to `position=0` and the same K/D the policy ships. |

The `ObservationManager` (and every `ObservationTerm`) mirrors the C++
side **structurally** — same term names, same scaling convention
`out = (q - default) * scale`, same flat-`ndarray` observation contract.
A policy debugged in Python promotes to the C++ `RLPolicyController` tier
without observation-indexing drift.

See [Policy runner](policy_runner.md) for the full ONNX metadata schema,
launch args, and the dataset-resolution order.

### `bar_bringup_lite` / `bar_bringup_prime`

The "main()" of the project. Each robot ships **two parallel launches**
(franka_ros2-style per-robot bringup — there is no top-level
`bringup.launch.py`):

| Launch | Hardware path | Selected xacro args |
|---|---|---|
| `real.launch.py` | `bar_hw_robstride` / `bar_hw_sito` over SocketCAN (+ EtherCAT for Prime) | `use_fake_hardware:=false use_sim:=false` |
| `mujoco.launch.py` | `mujoco_ros2_control/MujocoSystem` inside `mujoco_sim` | `use_sim:=true` |

Both launches:

1. Expand the robot xacro.
2. Start either `ros2_control_node` (real) or `mujoco_sim` (sim, with
   `MujocoRos2ControlPlugin` loaded as a pluginlib physics plugin).
3. Start `robot_state_publisher`.
4. Spawn `joint_state_broadcaster` (active) + `zero_torque_controller`
   (active) + the four remaining mode controllers (inactive).
5. Start `mode_manager`.
6. Optionally start `joy_node`.

`bar_bringup_lite/config/sim_overrides.yaml` adds `use_sim_time:=true`
on top of `bar_lite_controllers.yaml` for the MuJoCo path.
`bar_bringup_prime/config/ethercat.yaml` configures the IgH master for
Prime real-hardware bringup.

The `bar_simulation` package this used to live in was retired
(2026-05-12): its launch glue moved into `bar_bringup_lite/launch/mujoco.launch.py`,
its `sim_overrides.yaml` moved into `bar_bringup_lite/config/`.

## External (vcs-imported, not in this repo)

All four are pinned to specific commit SHAs in `bar.repos` — see the
[installation page](../quick_start/installation.md#3-clone-and-import-dependencies).