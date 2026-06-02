# Packages

The control stack is split across **two sibling repos** that are
cloned side-by-side under `bar_ws/src/`:

- **[`T-K-233/bar_ros2`](https://github.com/T-K-233/bar_ros2)** —
  12 packages making up the unified low-level control surface (URDF,
  controllers including in-process ONNX inference, hardware plugins, the
  launch-time policy-prep tool, both Lite and Prime bringups), plus a
  pip-only `bar_msgs_dds` package for off-ROS (Tier-3) clients. No
  task-specific code.
- **[`T-K-233/pianist_ros2`](https://github.com/T-K-233/pianist_ros2)** —
  4 packages implementing the **piano playing** task on top of
  `bar_ros2`: piano MJCF assets, a scene-composition launch, the
  piano-specific messages, and a `pianist_policy` package shipping the
  piano `prepare` tool + live key-state nodes.

The split is deliberate. `bar_ros2` is robot/control infrastructure
that every task reuses; `pianist_ros2` is the first concrete task
following the pattern. New task families (locomotion-task, dexterous
grasping, etc.) follow the same shape — a sibling repo depending on
`bar_msgs` + `bar_policy`, with its own bringup launch and a
`<task>_policy prepare` tool. The learned policy itself always runs
**in-process** in the shared C++ `RLPolicyController`; what differs per
task is the `.onnx` + `.mcap` and the prepare tool that produces them.

The rest of this page walks each package in turn. The
[`pianist_ros2` packages](#task-specific-packages-live-in-sibling-repos)
get their own section near the bottom.

## Per-package details (bar_ros2)

### `bar_common`

Header-only POD types and real-time helpers. Every C++ package in the workspace
depends on this.

| Header | Purpose |
|---|---|
| `mit_state.hpp` | `bar::MITState` — canonical observation struct (joint pos/vel/effort, IMU quat in **(w, x, y, z)** order, body-frame gyro/accel, last_action). Code-level schema, not a published topic. |
| `joint_index_map.hpp` | Bidirectional `name ↔ index` map, used to validate incoming `MITCommand` joint_names against a controller's claimed order. |
| `rt_utils.hpp` | RT-safe primitives: `monotonic_ns()`, `all_finite(...)`, `clamp(...)`. No allocations. |
| `loaned_interface_helpers.hpp` | `bar::set_cmd(...)` and `bar::get_state(...)` — discard wrappers for Jazzy's `[[nodiscard]] bool set_value()` and `get_optional<T>()` migration. Centralizes the Kilted migration to one file. |

### `bar_msgs`

Custom ROS 2 interfaces. Once a trained policy depends on one, it is **frozen**.

| Message | Used by |
|---|---|
| `MITCommand` | System 1/2 source → `RemotePolicyController`. The on-wire command format (also written internally by `RLPolicyController`). |
| `ControlMode` | `mode_manager` → `/control_mode` telemetry. |
| `StandbyState` | `StandbyController` → `/standby_controller/state` (`is_finished` gate for the `START_LOCOMOTION` / `START_REMOTE` intents). |
| `SafetyStatus` | every hardware plugin / controller → `/safety_status`. Per-bus `source` field; bitmask in `flags`. |

See [Messages reference](messages.md) for full schemas.

### `bar_msgs_dds`

**Not a colcon package** — a pip package (`COLCON_IGNORE`d) that gives
Tier-3 / off-ROS clients the `bar_msgs` types without `rclpy`. Its
`codegen/emit.py` parses `bar_msgs/msg/*.msg` with ROS's own
`rosidl_adapter` and emits `cyclonedds` `IdlStruct` dataclasses to a
committed `_generated.py`, baking in the rmw type-name mangling
(`pkg::msg::dds_::Name_`) and the `rt/` topic convention. It is **types +
wire conventions only** — no participant/transport.

| Aspect | Detail |
|---|---|
| Regenerate | `pixi run gen-dds` (needs `rosidl_adapter`, i.e. the ROS env) |
| Guard | `pixi run test-dds` (drift) + a CDR wire round-trip test |
| Runtime dep | `cyclonedds` only — no `rosidl`/`idlc` for consumers |
| Generated types | `MITCommand`, `ControlMode`, `SafetyStatus`, `StandbyState` + borrowed `std_msgs/Header`, `builtin_interfaces/Time`, `sensor_msgs/JointState` |

The `lite_sdk2` SDK builds its publisher/subscriber layer on top. See
[Talk to bar_ros2 from Python](../how_to/talk_to_bar_ros2_from_python.md).

### `bar_description_lite` / `bar_description_prime`

URDF / xacro / meshes / `<ros2_control>` blocks.

Layout (Lite shown):

```
bar_description_lite/
├── urdf/
│   ├── lite.urdf.xacro              # top-level kinematics (mode-aware: 14 or 17 joints)
│   └── lite.ros2_control.xacro      # 3-way plugin selector + per-joint static config
├── meshes/   *.stl                  # visual meshes
├── mjcf/     lite.xml               # MuJoCo physics model
├── config/   view_lite.rviz         # RViz config
└── launch/   view_lite.launch.py    # standalone visualization
```

The xacro selects between **three hardware backends** via args:

![xacro 3-way hardware selector](/img/diagrams/reference__packages__01_xacro_selector.svg)

The real-hardware path emits **two `<ros2_control>` blocks** (`LiteLeftArm`
carrying CAN ids 11..17, `LiteRightArm` carrying 21..27, with bus names
provided per-machine via the `hardware_config` YAML); sim and mock
collapse into one combined block. Per-joint static config (`can_id`,
`model`, `direction`, `lower_limit`, `upper_limit`, `torque_limit`,
`current_limit`) is emitted as `<param>` children only on the
real-hardware path. Values mirror
[`T-K-233/Lite-Lowlevel-Python`](https://github.com/T-K-233/Lite-Lowlevel-Python)'s
`configs/bimanual.yaml`; see
[Hardware specifications → Joint table](./hardware_specs.md#joint-table)
for the canonical values.

### `bar_drivers/bar_socketcan`

Reusable SocketCAN bus library. Owns the kernel-facing CAN socket lifecycle, a
dedicated I/O thread, and lock-free buffers. Per-actuator-family plugins
(`bar_robstride`, `bar_sito`) consume its synchronous `read_state()` /
`write_command()` API.

**Pattern reference**: mirrors the `soem_ros2` / `cleardrive_ros2` split from
`legged_control2`.

### `bar_devices/bar_robstride` and `bar_devices/bar_sito`

Per-actuator-family `hardware_interface::SystemInterface` plugins.
`bar_robstride` for Lite (and Prime's auxiliary joints if added later);
`bar_sito` for Prime's Sito side.

Both:
- Export the standard **3 state interfaces** (`<joint>/position`, `<joint>/velocity`, `<joint>/effort`).
- Export the **5 MIT-mode command interfaces** (`position`, `velocity`, `effort`, `stiffness`, `damping`).
- Read `can_interface` (system-level) and per-joint `can_id` from URDF params.
- Register via `pluginlib` against `hardware_interface::SystemInterface`.

`bar_robstride` additionally:

- Reads per-joint **`model`** (one of `rs-00`..`rs-06` — drives the MIT-mode
  scaling limits), **`direction`** (±1), **`lower_limit`** / **`upper_limit`**
  (joint-frame rad clipping at command time), and **`torque_limit`** /
  **`current_limit`** (Nm / A — opt-in firmware writes guarded by the
  hardware-level `write_firmware_limits` param) from URDF `<param>` children.
- Reads a system-level **`calibration_file`** (YAML,
  `{joint_name: {homing_offset, direction, id}}`) at `on_configure` and
  applies the standard convention at the bus boundary:
  ```
  read:  joint_pos    = direction * (raw_motor_pos - homing_offset)
  write: raw_motor_pos = direction * joint_pos     + homing_offset
         # velocity / effort: direction only, no offset
  ```
  Empty path = identity calibration (still applies `direction`). The YAML
  keeps the same per-joint keys as
  [`T-K-233/Lite-Lowlevel-Python`](https://github.com/T-K-233/Lite-Lowlevel-Python)'s
  JSON output, so values move between the two stacks unchanged.
- Publishes a `bar_msgs/SafetyStatus` on `/safety_status` (TRANSIENT_LOCAL,
  per-bus source field) with bit-flags for `BUS_OFF` / `RX_TIMEOUT` /
  `TX_QUEUE_OVERRUN` / `MOTOR_FAULT` / `TEMPERATURE_LIMIT` / `INVALID_FRAME`.
  `mode_manager` subscribes and auto-falls to DAMPING on any non-OK level.

Ships three CLI executables alongside the plugin:

| Executable | Purpose |
|---|---|
| `robstride_ping` | One-shot `GetDeviceId` ping at a specific id. Read-only. |
| `robstride_discover` | Scan an id range across one bus and print everyone that answers. Read-only, no Enable. |
| `mit_slider_gui` | Tk-Qt slider window publishing `Float64MultiArray` to `forward_command_controller/MultiInterfaceForwardCommandController`; manual command of position/velocity/effort/stiffness/damping per joint. |

### `bar_controllers`

Five mode-FSM controllers + the standalone `mode_manager` executable.

| Plugin | State | Source |
|---|---|---|
| `bar/ZeroTorqueController` | startup, safer fault fallback | `zero_torque_controller.cpp` |
| `bar/DampingController` | compliant fail-safe | `damping_controller.cpp` |
| `bar/StandbyController` | pose interpolation + gain ramp | `standby_controller.cpp` |
| `bar/RLPolicyController` | in-process ONNX inference (System 0) — every learned policy | `rl_policy_controller.cpp` |
| `bar/RemotePolicyController` | System 1/2 external-command ingress | `remote_policy_controller.cpp` |
| `mode_manager` exe | FSM orchestrator | `mode_manager.cpp` |

`RLPolicyController` now runs full in-process inference. Its runtime
modules live alongside the controllers in this package:

| Module | Responsibility |
|---|---|
| `OnnxPolicy` | onnxruntime C++ single-step inference. **Opt-in** (`ros-jazzy-onnxruntime-vendor`); falls back to `PlaceholderPolicy` (zeros) when not built in. |
| `ObservationManager` | Resolves each `observation_names` term — built-in proprioception → reference provider → topic-fed extern — into a preallocated buffer per tick. |
| `ReferenceProvider` (`McapTrackingReference` / `McapPianoReference`) | Loads the policy's `.mcap` motion bag whole at `on_configure` (via `rosbag2_cpp`) and integer-indexes it per tick. |
| `ActionMapper` | `pos = default + action * scale`, scattered across the full articulation; undriven joints pinned to `position=0` with the policy's `K`/`D`. |

The package reads the `.mcap` and configures every policy parameter from
the `rl_policy_controller` overlay that `bar_policy prepare` emits — it
never depends on `bar_policy` or any task message package.

See [Controllers reference](controllers.md).

### `bar_cli`

The unified verb/noun CLI surface (`bar bus ping`, `bar bus discover`,
`bar motor slider`, `bar viz rerun`, `bar viz viser`). An ament_python
package that thin-wraps the underlying executables shipped by
`bar_robstride` and `bar_bringup_lite`. Invoke as `bar <verb> <noun> …`
once `install/setup.bash` is sourced. (`pixi run bar …` is the
workspace-level shortcut — see
[Workspace shortcuts with pixi](../how_to/use_pixi_tasks.md).)

### `bar_policy`

An ament_python package that is a **launch-time prep tool**, not a
runtime node. Inference runs in-process in the C++ `RLPolicyController`
(System 0); `bar_policy` does the non-real-time, dependency-heavy work
once at launch. Its `prepare` console script (`ros2 run bar_policy
prepare`) composes:

| Module | Role |
|---|---|
| `checkpoint_loader.resolve_checkpoint` | Resolve a local `--checkpoint-file` or a `--wandb-run-path` to a local `.onnx`; cache W&B downloads under `~/.cache/bar_policy/wandb/<run_id>/`. |
| `policy_metadata.PolicyMetadata` | Typed access to the self-describing fields baked into the ONNX `custom_metadata_map` (joint names, gains, default pose, observation term names, dataset id, `policy_dt`, …). |
| `convert.tracking_frames` | Read the LeRobot episode and emit per-frame arrays (`[pos·3B][ori6d·6B]`). |
| `mcap_writer.write_motion_bag` | Write those frames to a single-episode rosbag2 `.mcap` bag (`std_msgs/Float32MultiArray`, via `rosbag2_py`). |
| `prepare.write_param_overlay` | Emit `rl_policy_params.yaml` — the ONNX metadata transcoded into `rl_policy_controller` params (joints, gains, scale, obs names, `motion_file`, `policy_checkpoint`, dims). |

The overlay is machine-generated from the checkpoint, so the `.onnx`
stays the single source of truth — nothing about the policy is restated
by hand in YAML. The C++ controller reads the `.mcap` and the overlay; it
never imports `bar_policy`.

See [Policy runner](policy_runner.md) for the full ONNX metadata schema,
the `prepare` CLI args, and the dataset-resolution order.

### Task-specific packages live in sibling repos

`bar_ros2` deliberately does not carry task-specific code. The piano
playing task lives in
[**`T-K-233/pianist_ros2`**](https://github.com/T-K-233/pianist_ros2),
cloned side-by-side under `bar_ws/src/`:

| Package | Build type | What it ships |
|---|---|---|
| `pianist_assets` | ament_cmake | Piano MJCF (`piano.xml`) installed under `<share>/pianist_assets/mjcf/`. |
| `pianist_bringup` | ament_cmake | `mujoco.launch.py` — composes a `_runtime_lite_piano.xml` scene next to `lite.xml` (so MuJoCo's `meshdir="../meshes/"` resolves), then delegates to `bar_bringup_lite/mujoco.launch.py` with `scene:=_runtime_lite_piano`. Also spawns `piano_state_bridge` so `/piano/key_state` exists on the sim path. |
| `pianist_msgs` | ament_cmake | Piano-task messages. No longer carries the key-state stream (that moved to a generic `std_msgs/Float32MultiArray` on `/piano/key_state`). |
| `pianist_policy` | ament_python | `prepare` console script + `piano_policy.launch.py` (runs the piano `prepare`, then loads the in-process `rl_policy_controller` inactive — the piano task is selected by the ONNX `task_type='piano'`). Also ships the live key-state nodes `piano_state_bridge` (sim) and `midi_keyboard_driver` (real USB-MIDI), both publishing `std_msgs/Float32MultiArray` on `/piano/key_state`, with a matching `midi_keyboard_driver.launch.py`. |

`pianist_policy`'s `prepare` reuses `bar_policy`'s checkpoint/metadata/
`.mcap` infrastructure, adding only the MIDI/song → key-state conversion.
There is no piano runner and no `pianist_msgs` dependency in
`bar_controllers`: the live key state arrives as a generic float array,
and the song reference is baked into the `.mcap` the controller loads.
New task families follow the same pattern: depend on `bar_msgs` +
`bar_policy`, ship a `<task>_policy prepare` tool that emits the overlay
+ `.mcap`, and a bringup launch composing onto
`bar_bringup_lite/mujoco.launch.py` or `…/real.launch.py`.

### `bar_bringup_lite` / `bar_bringup_prime`

The "main()" of the project. Each robot ships **parallel launches**
(franka_ros2-style per-robot bringup — there is no top-level
`bringup.launch.py`). For Lite, four total — three that boot a
control plane and one host-side viewer (see
[Concepts → Architecture → Deployment topology](../concepts/architecture.md#deployment-topology)
for which side runs which):

| Launch | Deployment side | Hardware path | Selected xacro args |
|---|---|---|---|
| `real.launch.py` | Robot onboard computer | `bar_robstride` / `bar_sito` over SocketCAN (+ EtherCAT for Prime) | `use_fake_hardware:=false use_sim:=false` |
| `mujoco.launch.py` | Single-machine sim/dev | `mujoco_ros2_control/MujocoSystem` inside `mujoco_sim` | `use_sim:=true` |
| `calibrate.launch.py` | Single-machine (robot benchtop) | `bar_robstride` with identity calibration + `calibrate_robot` observer | `use_fake_hardware:=false use_sim:=false` |
| `viz.launch.py` | Operator workstation (host) | DDS-consumer only; no controller_manager, no hardware | n/a — only subscribes |

The first two launches:

1. Expand the robot xacro.
2. Start either `ros2_control_node` (real) or `mujoco_sim` (sim, with
   `MujocoRos2ControlPlugin` loaded as a pluginlib physics plugin).
3. Start `robot_state_publisher`.
4. Spawn `joint_state_broadcaster` (active) + `zero_torque_controller`
   (active) + the four remaining mode controllers (inactive).
5. Start `mode_manager` (when `enable_mode_manager:=true`).
6. Start `joy_node` (when `enable_gamepad:=true`, which is the default).

`bar_bringup_lite/config/sim_overrides.yaml` adds `use_sim_time:=true`
on top of `bar_lite_controllers.yaml` for the MuJoCo path.
`bar_bringup_lite/config/calibration.yaml` is the per-physical-robot
zero offset that `bar_robstride` applies at the bus boundary on the
real path (regenerate via `ros2 launch bar_bringup_lite calibrate.launch.py` — see the
[Launch args](launch_args.md#bar_bringup_litelaunchcalibratelaunchpy)
page). `bar_bringup_lite/config/lite_hardware.yaml` is the per-machine
bus + joint mapping consumed by xacro. `bar_bringup_prime/config/ethercat.yaml`
configures the IgH master for Prime real-hardware bringup.

`bar_bringup_lite` also ships three operator-facing Python nodes.
The viewers are normally launched on the host side via
`ros2 launch bar_bringup_lite viz.launch.py` (which wraps them and
selects between them via `viewer:=viser|rerun`); direct
`ros2 run bar_bringup_lite rerun_viz` / `viser_viz` is the
single-machine sim/dev shortcut:

| Executable | Purpose |
|---|---|
| `calibrate_robot` | Calibration observer — subscribes `/robot_description` + `/lite/joint_states`, tracks per-joint (min, max), writes the homing-offset YAML on Ctrl+C. Driven by `calibrate.launch.py` (`ros2 launch bar_bringup_lite calibrate.launch.py`). |
| `rerun_viz` | Live URDF visualization in the **native** [rerun](https://rerun.io) viewer — auto-spawned subprocess by default, or `--connect host:port` to feed a remote one. Subscribes `/robot_description` (latched) and a `--joint-state-topic` (default `/lite/joint_states`); logs per-joint `Transform3D` to `/tf` at the tick rate. `rerun-sdk` ships in the workspace env. |
| `viser_viz` | Same subscriptions and resolution pattern, rendering into a **browser** at `http://<host>:<port>` (default `0.0.0.0:8080`) via [viser](https://github.com/nerfstudio-project/viser). Friendlier for headless robot machines and SSH workflows. `viser`, `yourdfpy`, and `scipy` ship in the workspace env. |

## External (vcs-imported, not in this repo)

Pinned in `bar.repos` and fetched via
`vcs import --input src/bar_ros2/bar.repos src` — see the
[installation page](../getting_started/installation.md#4-pull-third-party-sources).