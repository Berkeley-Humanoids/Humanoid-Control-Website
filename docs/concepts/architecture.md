# Software framework

This page describes **how the stack runs end-to-end at 50 Hz**: the
`ros2_control` cycle, the five-mode finite state machine that arbitrates which
controller is active, the in-process vs. out-of-process policy tiers, and the
safety / fallback model.

## The ros2_control cycle

`ros2_control` is the integration spine. `controller_manager` owns the
real-time loop. Every tick — 50 Hz by default for Lite — it performs three
steps:

![sequenceDiagram](/img/diagrams/overview__software_framework__01.svg)

**Constraints inside each phase:**

| Phase | What's allowed | What's forbidden |
|---|---|---|
| `read()` | swap lock-free buffer pointers, copy small POD | syscalls, allocations, DDS waits |
| `update()` | read state_interfaces_, write command_interfaces_, lock-free trylock for diag publishers | allocations, blocking, exceptions across the RT boundary |
| `write()` | stage frames into the bus library's outgoing queue | the actual CAN/EtherCAT syscall (that's the I/O thread's job) |

The I/O thread in each hardware plugin (`bar_hw_socketcan::SocketCanBus`,
`ethercat_driver_ros2`'s EtherLAB master thread) is **separate** from the
controller-manager thread. RT-safety is preserved by making `read()` /
`write()` allocation-free buffer swaps.

:::tip[Why MIT-mode lives in the hardware plugin, not the controller]
The torque computation
`tau = K_p (q_cmd - q) + K_d (dot q_cmd - dot q) + tau_ff`
runs **on the Robstride motor firmware** (real hardware) or **on MuJoCo's
qfrc_applied step** (sim). The controller just writes five numbers per joint
per tick. This is the same factoring used by MIT Cheetah / Mini Cheetah and
by Berkeley's earlier Humanoid-Control deployment.
:::

## Five-mode finite state machine

The whole control surface boils down to **one active controller at a time**,
selected by `mode_manager`. `joint_state_broadcaster` runs alongside as the
always-on state stream.

![stateDiagram-v2](/img/diagrams/overview__software_framework__02.svg)

Behavior per state:

| State | Plugin | What it writes |
|---|---|---|
| **ZERO_TORQUE** | `bar/ZeroTorqueController` | 0 to all 5 cmd interfaces. Startup default, fault fallback. |
| **DAMPING** | `bar/DampingController` | `K=0`, `D=damping value`, `q_cmd=q_captured` — soft under gravity, resists velocity. |
| **STANDBY** | `bar/StandbyController` | Linear pose interpolation through a YAML sequence; ramps `K_p / K_d` on first segment. Publishes `StandbyState` with `is_finished`. |
| **LOCOMOTION** | `bar/RLPolicyController` | In-process ONNX inference; YAML-driven obs packing + action mapping. |
| **REMOTE** | `bar/RemotePolicyController` | Thin executor for an out-of-process Python policy; subscribes `~/command` (`MITAction`) with stale-command gating. |

### Transition mechanics

Every transition is **one `switch_controller` service call** to the
controller_manager (STRICT strictness, async). The `mode_manager` node is a
plain `rclcpp::Node` that subscribes:

- `/joy` (gamepad intents)
- raw keyboard via `termios` (auto-disabled on non-TTY stdin)
- `/standby_controller/state` (the `is_finished` gate for the two `START_*` intents)
- `/safety_status` (the auto-DAMP trigger)

…and publishes `/control_mode` telemetry at tick rate.

## Two parallel policy tiers

The "active policy" mode comes in **two flavors** that share the exact same
observation/action contract:

![flowchart TB](/img/diagrams/overview__software_framework__04.svg)

**Key property**: the Python `ObservationManager` mirrors the C++ one
structurally — same term names (`JointPositionTerm`, `JointVelocityTerm`,
`LastActionTerm`, `ImuFieldTerm`, `ReferenceProviderTerm`), same scaling
convention `out = (q - q_default) * scale`, same flat-`ndarray`
observation contract. **A policy debugged in Python can be promoted to C++
without observation-indexing drift.**

The Python `ObservationManager` also exposes two **lifecycle hooks** that
the C++ side will eventually mirror:

- `reset()` — clear per-term state (e.g. `LastActionTerm` zero-init) and
  rewind any attached reference provider. Called on controller activation.
- `record_action(action)` — refresh `LastActionTerm` with the action the
  runner just emitted, then step the reference provider so the dataset
  frame advances exactly once per policy tick.

Today's **out-of-process tier is the real ONNX path**: `bar_policy`'s
`remote_policy_runner` loads an ONNX checkpoint, parses self-describing
metadata baked into the file (joint names, gains, default pose, dataset
pointer), and publishes `MITAction` to `RemotePolicyController`. The
in-process `RLPolicyController` is still wired to a `ConstantHoldPolicy`
stub — same metadata schema will land in C++ when locomotion graduates
to in-process inference. See [Policy runner](../reference/policy_runner.md).

`MITState` itself is a **code-level** schema (a `bar::MITState` POD in
C++, a matching `@dataclass` in Python). It is not a published topic —
observations are assembled in-process from `/joint_states` (the always-on
broadcaster) and `/imu/data` (the IMU driver).

## Frozen schemas

A handful of artifacts are **frozen once a trained policy depends on them**:

| Artifact | Frozen because |
|---|---|
| `bar_msgs/MITAction` | trained policies emit this field-by-field over DDS |
| Joint order in `bar_*_controllers.yaml` | trained policies index into this order |
| `MITState` struct + Python dataclass | both sides agree on `joint_position`/`joint_velocity`/IMU layout |
| Observation term scale + default vectors | shifts mean retraining |

Once a policy ships to a piano-playing or locomotion run, changing any of
these forces retraining. Keep this in mind when refactoring.

## Safety and fault handling

Safety is **layered** — no single ROS node is treated as the whole safety
system:

Concrete examples:

- A Robstride bus-off → `bar_hw_robstride` publishes `SafetyStatus{level=FAULT,
  source="bar_hw_robstride/can0", flags=BUS_OFF}` → `mode_manager` requests a
  STRICT switch to DAMPING. If DAMPING fails (e.g. command interfaces
  unavailable), `mode_manager` falls back to ZERO_TORQUE.
- A `RemotePolicyController` whose Python publisher stalls for >100 ms
  (`stale_command_timeout_ms` default) writes **passive commands** (zero
  stiffness/damping) instead of zero-order-holding stale output. The policy
  can stay subscribed and resume cleanly.
- An RL policy returning NaN in its action vector → `RLPolicyController`
  detects via `bar::rt::all_finite(...)` and returns `return_type::ERROR`,
  triggering `fallback_controllers` in the CM YAML.

## Next

- [`mode_manager` source](https://github.com/T-K-233/bar_ros2/blob/main/bar_controllers/src/mode_manager.cpp)
  — the FSM is ~150 lines of C++; readable in one sitting.
- [Lite 101](../getting_started/lite_101.md) — see all of this run end-to-end
  against mock hardware and MuJoCo.
- [Controllers reference](../reference/controllers.md) — per-controller
  parameter tables.