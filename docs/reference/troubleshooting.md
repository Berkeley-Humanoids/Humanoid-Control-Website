# Troubleshooting

A flat list of the symptoms we've actually seen, in rough frequency
order. Each entry has the one-line diagnosis and the page that
explains it. The intent is to short-circuit the "ah, that one again"
moment.

## Bringup boots, but every joint reads exactly 0.0

**Diagnosis**: the actuators are not Enabled — usually because the
Enable frame was dropped before the motors could ACK.

**Why**: `RobstrideSystem::on_activate` sends one `Enable` per joint,
back-to-back into the kernel TX qdisc (default `txqueuelen=10`). With
14 joints and a few extra frames, the qdisc can fill if the motors
aren't ACKing TX. No ACK → no qdisc drain → ENOBUFS → frames dropped.
The motors miss their Enable and never come out of disabled state.

**The most common cause of no ACKs is motor power being off.**

**Fix**:
1. Confirm motor power. Walls and 24 V supply both on; e-stop released.
2. Re-launch. The Enable burst should now succeed.

If power is verified on but ENOBUFS persists, see [Diagnose ENOBUFS](../how_to/diagnose_enobufs.md).

## `Failed to open SocketCAN interface 'canN'`

**Diagnosis**: the CAN interface isn't up (`LOWER_UP` / `state UP`).

**Why**: `ip link set canN down` on reboot, or USB adapter was hot-plugged
after the kernel last saw it.

**Fix**: bring the bus up at the Robstride bitrate (1 Mbps):

```bash
sudo ip link set can0 down 2>/dev/null
sudo ip link set can0 up type can bitrate 1000000
# Same for can1
```

The plugin's `SIOCGIFFLAGS` guard catches this case explicitly so the
error log is one line — no silent hang.

## `Loaded calibration_file '...' (0/N joints matched)`

**Diagnosis**: the JSON keys don't line up with any of the joint names
the plugin's seeing from URDF.

**Why**: usually one of:
- The URDF was renamed, but `calibration.json` is from an older revision.
- The path resolved to the wrong file (typo, stale install share).
- You hand-edited the JSON and broke a key.

**Fix**: open the file, compare `keys` against
`bar_lite_controllers.yaml`'s `joints:` list. They must match
character-for-character. Or regenerate the file via
[Calibrate the zero pose](../how_to/calibrate_zero_pose.md) — the
output uses live URDF names.

## `Failed to configure controller 'rl_policy_controller'`

**Diagnosis**: `RLPolicyController::on_configure` rejected
`observation_dim=0, action_dim=0` (the placeholder values in
`bar_lite_controllers.yaml`).

**Why**: we don't yet have a locomotion policy with a frozen metadata
schema. The placeholder zeros are a tombstone — the controller's
own validation refuses to come up against them.

**Fix**: drop `rl_policy_controller` from your launch's
`inactive_spawner` batch (Lite's `real.launch.py` already does this
for the real-hardware path; `mujoco.launch.py` doesn't, and we accept
the configure failure there since MuJoCo bringups don't currently
need RL). Restore once the policy has real `observation_dim` /
`action_dim` values.

## ENOBUFS / "Network is down" warnings during bringup

**Diagnosis**: kernel TX qdisc full, frames being dropped at write
time. Almost always = motors not ACKing.

**Why**: motor power off (most common), bus stuck `BUS-OFF`, or
hardware adapter overload at very high frame rates.

**Fix**:
1. **Motor power off** — power on, re-launch. Resolves 99% of cases.
2. **`BUS-OFF`** — `ip -d link show canN` will say so. Power-cycle
   the USB-to-CAN adapter.
3. **High-rate overload** — only relevant with many joints + tight
   update_rate. Lower `controller_manager.update_rate` in
   `bar_lite_controllers.yaml`, or bump `sudo ip link set canN
   txqueuelen 100` (default 10).

Full walk: [Diagnose ENOBUFS](../how_to/diagnose_enobufs.md).

## `/safety_status` shows `flags != 0`

**Diagnosis**: the plugin observed an actuator-side fault on at least
one tick. Even a single bad frame trips a bit until `on_activate`
clears it.

The bit table:

| Flag | Meaning |
|---|---|
| `FLAG_BUS_OFF` | Kernel CAN socket open failed (sticky — survives until configure). |
| `FLAG_RX_TIMEOUT` | A joint went silent for > `rx_timeout_ms`. |
| `FLAG_TX_QUEUE_OVERRUN` | Bus library's outbound ring filled (RT producer faster than I/O thread). |
| `FLAG_MOTOR_FAULT` | Robstride status / fault report reported a non-OK condition. |
| `FLAG_TEMPERATURE_LIMIT` | Specifically overtemp, surfaced separately for visibility. |
| `FLAG_INVALID_FRAME` | Frame on the bus that we couldn't parse (wrong comm-type, wrong DLC). |

**Fix**: see [Recover from a fault](../how_to/recover_from_fault.md).

## `mode_manager` rejects an intent

**Diagnosis**: the FSM transition isn't allowed from your current
state. `mode_manager` writes the reason into
`/control_mode.status_message`:

```
ros2 topic echo /control_mode
# status_message: "Rejected LOAD: requires DAMPING (currently ZERO_TORQUE)"
```

**Fix**: walk the legal path. `LOAD` requires DAMPING; `START_*`
requires STANDBY with `is_finished:true`; `QUIT` requires
ZERO_TORQUE or DAMPING. See [Five-mode FSM](../concepts/five_mode_fsm.md).

## Spawner times out waiting for `/controller_manager/list_controllers`

**Diagnosis**: the controller_manager process isn't fully up yet.
Normal on a cold boot; usually clears within ~2 s. If the wait
exceeds ~10 s, something is wrong with the launch (hardware plugin
crashed, ROS domain mismatch, robot_state_publisher hung on a stale
xacro).

**Fix**: look at the controller_manager log. If it's missing
entirely, the hardware plugin probably threw during `on_init` /
`on_configure` and took the process down. Common causes:
- URDF expansion failed (run `xacro <file>` directly to see the error).
- `bar_hw_robstride` was rebuilt with an ABI-incompatible bump but
  the .so wasn't reinstalled. `colcon build --packages-select
  bar_hw_robstride --symlink-install`.

## DDS discovery fails between `ros2 launch` and `ros2 topic ...`

**Diagnosis**: `ROS_DOMAIN_ID` mismatch, or two `ros2 launch`
instances running on the same domain on the same machine.

**Fix**: `echo $ROS_DOMAIN_ID` in both terminals. They must match (or
both unset = domain 0). If two launches are colliding, pick distinct
domains via `ROS_DOMAIN_ID=N` in each.

## ENOBUFS warnings *while a controller is active* (not boot)

**Diagnosis**: outbound CAN traffic exceeds the bus's drain rate over
sustained time. Usually a programming bug in a custom controller
(unbounded retries, mis-rate'd publish loop, etc).

**Fix**: check `tx_failed` counters in the SafetyStatus output. If a
controller is misbehaving, deactivate it and replace with
`zero_torque`. Otherwise raise `txqueuelen` as a workaround while you
diagnose.

## Cross-references

- **Boot-time bringup checks**: [First real-hardware bringup → Common boot-time failures](../how_to/first_real_bringup.md#common-boot-time-failures)
- **Calibration drift**: [Calibrate the zero pose](../how_to/calibrate_zero_pose.md)
- **Bus / qdisc nitty-gritty**: [Diagnose ENOBUFS](../how_to/diagnose_enobufs.md)
- **Per-flag fault meaning + recovery**: [Recover from a fault](../how_to/recover_from_fault.md)
- **FSM transition rules**: [Five-mode FSM](../concepts/five_mode_fsm.md)
