# Five-mode FSM

The operator-facing control surface is a **finite state machine over
controllers**. Each "mode" is exactly one `controller_interface::ControllerInterface`
plugin, and **only one mode controller is active at any time** — the
controller_manager's interface-claiming machinery enforces that
mutual exclusion mechanically. `joint_state_broadcaster` is the
always-on telemetry stream alongside whichever mode is active.

![Five-mode FSM with joy bindings](/img/diagrams/concepts__five_mode_fsm__01.svg)

## Why a state machine

Three reasons, all from operator UX:

1. **Single-axis safety.** "Send DAMP" should land you somewhere safe
   regardless of where you are now. A flat set of controllers with
   ad-hoc transitions would have to enumerate `N²` "from X to DAMP"
   paths; an FSM with one universal DAMP edge has one rule.
2. **Gated transitions.** STANDBY → REMOTE shouldn't fire while
   STANDBY is still mid-trajectory. The state machine gives us a
   natural place to express "only allowed when `is_finished:true`".
3. **Single source of truth for `/control_mode`.** Observers (rqt
   dashboards, loggers, the cheat-sheet you print) read one topic to
   know what the robot is doing.

The cost is a little extra ceremony for the operator (you can't go
ZERO_TORQUE → REMOTE directly), but that ceremony is the safety
property.

## The five modes

| Mode | Plugin | What it writes per tick | Use it for |
|---|---|---|---|
| **ZERO_TORQUE** | `humanoid_control::ZeroTorqueController` | `0` to all 5 MIT interfaces on every joint | Startup default. Fault fallback when DAMPING can't be applied (e.g. state not yet valid). Robot is alive but inert. |
| **DAMPING** | `humanoid_control::DampingController` | `stiffness=0`, `damping=damping_value`, `position=captured`, `velocity=0`, `effort=0` | Compliant fail-safe. Robot stays soft under gravity but resists velocity. The state you pass through between operator-driven transitions. |
| **STANDBY** | `humanoid_control::StandbyController` | Interpolated `position` along a YAML pose sequence; `K_p`/`K_d` ramped 0→target during segment 0 | Animate the arms to the piano-ready pose with gain ramp-in. Publishes `~/state.is_finished` so transitions out are gated correctly. |
| **LOCOMOTION** | `humanoid_control::RLPolicyController` | In-process ONNX inference (low-latency, C++): packs obs, replays the `.mcap` motion reference, writes commands | **Every learned policy** — tracking, piano, locomotion. They differ only by the loaded `.onnx` + `.mcap`; the ONNX `task_type` selects the term set. This is the System 0 real-time path. |
| **REMOTE** | `humanoid_control::RemotePolicyController` | `MITCommand` consumed from `~/command` over DDS | System 1/2 external-command ingress: a *non*-real-time source publishes commands (gravity-comp today via `Lite-Gravity-Compensation`; VLA / manipulation later). Not used by the learned policies. |

Full per-controller parameter tables live in
[Reference → Controllers](../reference/controllers.md).

## Transition rules

Encoded in `humanoid_controllers/src/mode_manager.cpp`. The operator's
gamepad intent goes through `dispatch_intent`, which gates based on the
current mode:

```
DAMP             (X)        : any state            → DAMPING
LOAD             (L1+A/B)   : DAMPING              → STANDBY
START_LOCOMOTION (R1+A)     : STANDBY ∧ is_finished → LOCOMOTION
START_REMOTE     (R1+B)     : STANDBY ∧ is_finished → REMOTE
QUIT             (BACK)     : ZERO_TORQUE or DAMPING → rclcpp::shutdown()
                              (rejected from active-policy states —
                               operator must DAMP first)
```

The same transitions are also exposed as `std_srvs/Trigger` services
under `/humanoid_control/mode/{damp,load,start_remote,start_locomotion,quit}`, so a
keyboardless lab box can drive the FSM with `ros2 service call …`.

`mode_manager` publishes `/control_mode` (`humanoid_control_msgs/ControlMode`) at
50 Hz. When an intent is rejected, the rejection reason goes into
`status_message` so operators see *why* a button didn't take effect.

To avoid a startup race where the operator's first DAMP press lands
before all controllers have finished loading, `mode_manager` polls
`list_controllers` every 25 ticks (500 ms at 50 Hz) so newly loaded
controllers become visible to `dispatch_intent` immediately.

## The auto-DAMP path (safety)

Every hardware plugin publishes `/safety_status` (`humanoid_control_msgs/SafetyStatus`)
on a TRANSIENT_LOCAL QoS, with a bitmask of `BUS_OFF`, `RX_TIMEOUT`,
`TX_QUEUE_OVERRUN`, `MOTOR_FAULT`, `TEMPERATURE_LIMIT`, `INVALID_FRAME`.
`mode_manager` subscribes. On any non-`OK` level it requests DAMPING
with a STRICT switch:

```
SafetyStatus.level != OK   →   request_mode(DAMPING)
```

If DAMPING itself fails to activate (e.g. the bus is gone and the
command interfaces are unavailable), `mode_manager` falls further
back to ZERO_TORQUE and writes the failure reason into
`/control_mode.status_message`. The chain is intentionally
**conservative-to-most-conservative**: REMOTE → DAMPING → ZERO_TORQUE.

See [Concepts → Safety pipeline](./safety_pipeline.md) for what each
flag means and which plugin sets it.

## Pairing convention for the START combos

`L1+A → R1+A` is the "locomotion" (local) path; `L1+B → R1+B` is the
"remote policy" path. **Both LOAD combos land in the same STANDBY** —
the A/B distinction is just operator UX so your thumb stays on one
column through `LOAD → START`. The FSM doesn't enforce it; you could
press `L1+A` then `R1+B` and the state machine would happily route
you DAMPING → STANDBY → REMOTE.

The reason for two combos at all is the **policy target is chosen at
runtime**, not by a launch arg. There's no `policy_mode` parameter on
`mode_manager` — the choice between `RemotePolicyController` and
`RLPolicyController` is the button that ends the START combo.

## What mode_manager is *not*

- **Not a safety system on its own.** Hardware plugins still have to
  detect transport failures and publish them; `mode_manager` only
  reacts to what plugins report. The plugin enforces "cannot apply
  command" (returns the right `return_type`), the FSM enforces "this
  transition is not allowed", and the controller_manager enforces "no
  two controllers claim the same command interface".
- **Not the controller_manager.** `mode_manager` is a regular
  `rclcpp::Node` executable that calls `switch_controller` as a
  client. The actual interface-claiming and `update()` orchestration
  is done by `controller_manager` running inside `ros2_control_node`.
- **Not running during calibration.** `calibrate.launch.py` passes
  `enable_mode_manager:=false` so the FSM doesn't interfere with the
  raw `/lite/joint_states` sampling. The operator drives controllers
  directly via `switch_controllers` if they want a mode change during
  calibration.

## See also

- [Reference → Controllers](../reference/controllers.md) — per-plugin parameter tables.
- [Concepts → Safety pipeline](./safety_pipeline.md) — what triggers auto-DAMP.
- [How-to → Switch controllers without the FSM](../how_to/switch_controllers_manually.md).
- [`mode_manager` source](https://github.com/Berkeley-Humanoids/humanoid_control/blob/main/humanoid_controllers/src/mode_manager.cpp).
