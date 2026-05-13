# Messages (bar_msgs)

Custom ROS 2 interfaces. **Frozen** once a trained policy depends on the
schema (changing the layout forces retraining).

## Topology

![flowchart TB](/img/diagrams/reference__messages__01.svg)

## `MITAction`

The action format sent from any out-of-process policy to
`RemotePolicyController`. Mirrors the **five MIT-mode command interfaces**
one-to-one.

```
std_msgs/Header header
string[] joint_names      # validated against the controller's claimed order
float64[] position
float64[] velocity
float64[] effort
float64[] stiffness
float64[] damping
```

All arrays must have the same length as `joint_names`. The controller rejects
the message if the order doesn't match its `joints:` parameter.

:::tip[Why all five fields, every message]
Sending only `position` (Cartesian-style) would force the receiver to assume
defaults for the rest. By making the policy send all five, the **intent is
explicit**: a "position-only" command would still send `velocity=0`,
`stiffness=Kp_target`, `damping=Kd_target`, `effort=0` — making the controller
re-creation fully reproducible.
:::

## `ControlMode`

Mode-FSM telemetry, published by `mode_manager` at tick rate (50 Hz).

```
std_msgs/Header header

uint8 ZERO_TORQUE = 0
uint8 DAMPING     = 1
uint8 STANDBY     = 2
uint8 LOCOMOTION  = 3
uint8 REMOTE      = 4

uint8 mode
string controller_name      # spawned controller name (e.g. "damping_controller")
string status_message       # human-readable, may carry rejection reason
```

The numeric `mode` field uses the explicit constants above. Consumers should
match against the `uint8 <name> = <value>` defines, not hard-code integers.

## `StandbyState`

Published by `StandbyController` on `~/state` (which resolves to
`/standby_controller/state`) with `TRANSIENT_LOCAL` (latched) QoS so a
late-joining `mode_manager` immediately sees the most recent value.

```
std_msgs/Header header
uint32 current_segment    # index into the pose sequence
uint32 total_segments
float64 progress          # [0, 1] within the current segment
bool is_finished          # true once final pose + final gains reached
```

`mode_manager` gates the `START` intent (STANDBY → LOCOMOTION/REMOTE) on
`is_finished == true`.

## `SafetyStatus`

Layered safety telemetry. Any hardware plugin or controller may publish; the
`flags` bitmask is **plugin-specific**.

```
std_msgs/Header header

uint8 OK       = 0
uint8 WARNING  = 1   # degraded but commands still honored
uint8 FAULT    = 2   # commands no longer guaranteed; transition recommended
uint8 CRITICAL = 3   # immediate fault fallback required

uint8 level
string source       # e.g. "bar_hw_robstride/can0", "rl_policy_controller"
uint32 flags        # plugin-specific bitmask
string message
```

:::warning[Concrete `flags` bit assignments are still TBD]
Each hardware plugin owes a documented bit table. Until those land, treat
`flags` as opaque-but-monotonic: same source + same flags = same fault class.
:::

## `VLAGoal` (stub)

Goal description for a vision-language-action manipulation policy. The full
surface will be finalized when the first VLA policy is wired into
`bar_policy`.

```
std_msgs/Header header
string instruction                # natural language
sensor_msgs/Image[] images        # optional task-grounding images
```

Frozen as soon as a trained VLA depends on it.