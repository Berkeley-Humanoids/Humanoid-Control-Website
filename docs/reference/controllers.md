# Controllers + FSM

Five `controller_interface::ControllerInterface` plugins, one standalone
`rclcpp::Node` orchestrator. **Only one mode controller is active at a time**;
`joint_state_broadcaster` runs always.

## FSM summary

See [Concepts → Architecture](../concepts/architecture.md#five-mode-finite-state-machine)
for the annotated version including safety-fault edges.

## Plugin-by-plugin

### `bar/ZeroTorqueController`

**Role**: startup default; safer fault fallback.

**Claims**: position, velocity, effort, stiffness, damping on every joint.

**Writes** every tick: `0` to all 5 command interfaces.

**Parameters**:

| Param | Type | Default | Description |
|---|---|---|---|
| `joints` | `string[]` | — | Required. Joint names to claim (must match URDF). |

### `bar/DampingController`

**Role**: compliant fail-safe. The robot stays **soft under gravity** but
**resists velocity**.

**Mechanics**: on `on_activate`, captures the current joint positions into
`captured_position_`. Every tick writes:

| Interface | Value |
|---|---|
| `position` | `captured_position_[i]` |
| `velocity` | `0` |
| `effort`   | `0` |
| `stiffness`| `0` |
| `damping`  | `damping_value_[i]` |

With `stiffness = 0`, no restoring force; with `damping > 0`, viscous
resistance.

**Parameters**:

| Param | Type | Default | Description |
|---|---|---|---|
| `joints` | `string[]` | — | Required. |
| `damping` | `float64[]` | `[]` | Per-joint damping. Empty → use `damping_scalar`. |
| `damping_scalar` | `float64` | `1.0` | Used when `damping` is empty. |

### `bar/StandbyController`

**Role**: linearly interpolate joint positions through a pose sequence; ramp
`K_p / K_d` from `0` to target gains during the **first** segment so
activation never snaps.

**Parameters**:

| Param | Type | Description |
|---|---|---|
| `joints` | `string[]` | Required. |
| `target_stiffness` | `float64[]` | Per-joint target `K_p` when ramp finishes. |
| `target_damping` | `float64[]` | Per-joint target `K_d`. |
| `segment_durations` | `float64[]` | Seconds per pose segment. Length determines how many pose segments are expected. |
| `pose_segment_<i>` | `float64[]` | Per-segment target pose vector; one parameter per segment index in `[0, len(segment_durations))`. Each is a per-joint position array sized to `len(joints)`. |

**Publishes**: `~/state` (`bar_msgs/StandbyState`) with `TRANSIENT_LOCAL` QoS
so `mode_manager` sees `is_finished` even on late join.

:::tip[How the bundled config interpolates]
`bar_lite_controllers.yaml` ships **two segments**: `pose_segment_0` is
the zero-pose (where the robot starts), `pose_segment_1` is the
piano-ready training default — mirror-symmetric across the sagittal plane
(shoulders roll outward, elbows bend in, wrists relax). The LOAD intent
therefore animates the arms from zero to the piano-ready pose over two
2-second segments while ramping `K_p` / `K_d` from 0 to the target gains
during the first segment.
:::

`fallback_controllers: ["damping_controller"]` is set on the
controller-manager side so any non-`OK` `return_type` from `update()`
auto-deactivates Standby and activates Damping.

### `bar/RLPolicyController`

**Role**: in-process ONNX inference for low-latency RL (locomotion target).
YAML-driven observation packing + action mapping.

**Parameters**:

| Param | Type | Description |
|---|---|---|
| `joints` | `string[]` | Required. |
| `default_joint_position` | `float64[]` | Used as `q_default` in obs scaling and `pos_cmd = q_default + scale * a`. |
| `action_scale` | `float64[]` | Per-joint scale. |
| `stiffness`, `damping` | `float64[]` | Per-joint MIT gains written every tick. |
| `observation_dim`, `action_dim` | `int` | Sizes; 0 falls back to `ConstantHoldPolicy` stub. |
| `imu_topic` | `string` | Default `/imu/data`. |

:::tip[C++ tier is still the stub]
The current `RLPolicyController` uses `ConstantHoldPolicy` (zeros) as a
placeholder. The **out-of-process Python tier in `bar_policy` is the real
ONNX runner today** — see [Policy runner](policy_runner.md). When the
locomotion policy graduates to in-process inference, the C++ runner will
adopt the same `PolicyMetadata` schema so the YAML and ONNX file stay
interchangeable across tiers.
:::

### `bar/RemotePolicyController`

**Role**: thin executor for an out-of-process policy. Subscribes
`~/command` (`MITAction`, `RELIABLE` QoS depth 4) and hands off via
`realtime_tools::RealtimeBuffer` to the RT update().

**Parameters**:

| Param | Type | Default | Description |
|---|---|---|---|
| `joints` | `string[]` | — | Required. |
| `stale_command_policy` | `string` | `passive` | `passive` or `hold` |
| `stale_command_timeout_ms` | `int` | `100` | (≈ 5 ticks at 50 Hz) |

The controller **rejects** any `MITAction` whose `joint_names` doesn't match
its claimed order, or whose array lengths don't all match `joints.size()`.

The companion **`remote_policy_runner` node** in `bar_policy` is what
publishes `MITAction` to this controller — it loads an ONNX policy, parses
its self-describing metadata, packs observations from `/joint_states` and
optionally a LeRobot reference dataset, and steps inference at
`policy_dt`. See [Policy runner](policy_runner.md) for the runner-side
contract.

### `mode_manager` (executable)

**NOT a controller plugin** — a regular `rclcpp::Node` compiled as the
`bar_controllers/mode_manager` executable.

| Input | Topic / source | Purpose |
|---|---|---|
| Gamepad | `/joy` (`sensor_msgs/Joy`) | DAMP / LOAD / START_LOCOMOTION / START_REMOTE / QUIT intents |
| Keyboard | termios on stdin (TTY only) | same intents (reader not yet implemented) |
| Standby done | `/standby_controller/state` (`StandbyState`) | gate the START intents on `is_finished` |
| Safety | `/safety_status` (`SafetyStatus`) | auto-fall to DAMPING on non-OK |

| Output | Topic | Purpose |
|---|---|---|
| FSM state | `/control_mode` (`ControlMode`) | tick-rate telemetry |
| Mode switch | `/controller_manager/switch_controller` | the actual transition |

**Joy bindings** (Xbox-layout defaults — remap via the `joy.*` params):

| Buttons | Intent | Target |
|---|---|---|
| `X` (2) | DAMP | `damping_controller` |
| `L1+A` (4+0) **or** `L1+B` (4+1) | LOAD | `standby_controller` |
| `R1+A` (5+0) | START_REMOTE | `remote_policy_controller` |
| `R1+B` (5+1) | START_LOCOMOTION | `rl_policy_controller` |
| `BACK` (6) | QUIT | `rclcpp::shutdown()` |

The two LOAD combos and two START combos are paired by **operator
convention**: `L1+A → R1+A` for the remote-policy path,
`L1+B → R1+B` for the locomotion path. The `LOAD` transition lands in
the same `STANDBY` state either way — the pairing just lets the
operator's thumb stay on the same column through the LOAD → START
sequence.

**Parameters**:

| Param | Type | Default | Description |
|---|---|---|---|
| `tick_rate_hz` | `float64` | `50.0` | timer rate |
| `controller_manager` | `string` | `/controller_manager` | CM namespace |
| `enable_keyboard` | `bool` | `true` | termios reader on stdin (not yet wired) |
| `joy.damp_button` | `int` | `2` | DAMP button index |
| `joy.quit_button` | `int` | `6` | QUIT button index |
| `joy.load_combo_remote` | `int[]` | `[4, 0]` | LOAD combo (remote-paired = L1+A) |
| `joy.load_combo_locomotion` | `int[]` | `[4, 1]` | LOAD combo (locomotion-paired = L1+B) |
| `joy.start_combo_remote` | `int[]` | `[5, 0]` | START_REMOTE combo (R1+A) |
| `joy.start_combo_locomotion` | `int[]` | `[5, 1]` | START_LOCOMOTION combo (R1+B) |

## Spawn order (in launch)

The launch spawns `zero_torque_controller` active independently — so even if
`mode_manager` dies, the robot is in the safe state.