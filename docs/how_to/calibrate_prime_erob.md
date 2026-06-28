# Calibrate the Prime eRob arms

Per-physical-robot recipe: regenerate `bar_bringup_prime/config/prime_calibration.yaml`
so each eRob (ZeroErr) joint's absolute encoder zero maps to the URDF's joint zero.
Same idea as [Calibrate the zero pose](./calibrate_zero_pose.md) for Lite — but the
eRob is a stiff CiA402 servo on EtherCAT, not a backdrivable MIT motor, so the
"make it limp" and "apply the offset" steps work differently.

## What the calibration does

The eRob output encoder is absolute (it keeps its zero across power cycles) with a
factory zero; the URDF defines a different joint zero. The offset bridges them,
exactly as on Lite:

```
joint_pos = direction * (raw_pos - homing_offset)
```

`direction` (plus/minus 1) is a wiring fact; `homing_offset` is per-physical-robot.
The full derivation — `homing_offset = 0.5 * ((min - lower) + (max - upper)) * direction`,
averaged over both mechanical stops — is on the
[Calibration math](../concepts/calibration_math.md) page.

The Lite/eRob difference is **where the offset is applied**. Lite owns its hardware
interface, so it subtracts `homing_offset` in `read()`/`write()`. The eRob runs on the
third-party `ethercat_driver`, which we do not fork — so `scripts/fold_calibration.py`
folds the offset into each joint's PDO `factor`/`offset` in a generated per-slave
config, and `real.launch.py` hands that to the xacro at launch via the
`erob_config_dir` argument. No drive-NVM writes; the calibration stays in one
git-tracked YAML.

## How the eRob differs from Lite

- **No MIT zero-torque.** The eRob runs CSP (Cyclic Synchronous Position); it has no
  stiffness/damping command interface. To hand-sweep, we turn it into a **velocity
  damper** by writing its internal loop gains.
- **The PID gate — `0x2383`.** Object `0x2383` ("Bus Regulation of PID", default 0 =
  off) gates whether bus-written loop gains are applied. **It must be set to 1 first**,
  or writes to the gain objects are silently ignored and the joint stays stiff. This is
  the single most common reason "the limp does nothing".
- **Damped-limp, one joint at a time.** Set position-loop gain `0x2382:01` to 0 (no
  stiffness) and velocity-loop integral `0x2381:02` to 0 (no spring-back), but **keep**
  the velocity-loop gain `0x2381:01` (damping) so gravity gives a slow controlled
  descent instead of freefall. On a heavy arm, limp one joint while the others stay
  held — `scripts/erob_limp_joint.sh` does exactly this (snapshot, gate on, kp/ki to 0,
  sweep, restore on exit).

## Prerequisites

- The arms are **supported** (jig, table, or a helper). Damping limits the *speed* of a
  fall, not the position — the shoulder still holds the whole arm.
- The IgH EtherCAT master is running and the drives are powered. See
  [First real-hardware bringup](./first_real_bringup.md).
- e-stop in reach.

## Step 1 — Bring up the chain

Bring the eRob drives to CSP Operation-Enabled. On the full robot this is
`calibrate.launch.py`; while only a subset is wired, bring up just those drives (the
full `real.launch.py` expects all 13 eRob plus the Sito wrists, so it will not activate
on a partial chain). Bring-up is slow — roughly 6 s per drive, serial, in the IgH/eRob
handshake — so a 10-drive chain takes about 70 s. That is a fixed cost of the eRob
bring-up (not config-tunable: DC, PDO size, and `control_frequency` were all ruled out).

Activate the broadcaster so `/joint_states` flows:

```bash
ros2 control load_controller joint_state_broadcaster --set-state active
```

## Step 2 — Start the tracker

```bash
ros2 run bar_bringup_prime calibrate_erob \
  --output ~/prime_calibration.yaml --topic /joint_states
```

`calibrate_erob` discovers the eRob joints from the URDF `ec_module`s, reads each
joint's `lower`/`upper` from the kinematic limits, and tracks per-joint `min`/`max` of
`/joint_states` with a live readout. (Pass `--prior <file>` to preserve already-swept
joints — e.g. calibrate the right arm without re-sweeping the left.)

## Step 3 — Damped-limp and sweep each joint

For each ring position, support the joint, then:

```bash
ros2 run bar_bringup_prime erob_limp_joint <ring_pos>      # e.g. 4
```

The joint goes damped-limp (the read-back prints `Kp=0`, confirming the `0x2383` gate
worked). Sweep it firmly to **both** mechanical stops — watch the tracker's `sweep`
grow past about 0.5 rad so it is not skipped — return near neutral, and press Enter to
re-hold. If a joint is too stiff to move, pass a smaller damping value as a second
argument. Work distal to proximal; do the shoulder last.

When every joint is swept, **Ctrl-C the tracker** — it writes the YAML and flags any
joint with too small a sweep (skipped, prior kept) or `abs(homing_offset) > pi` (a
`direction` sign flip — set `-1` and re-sweep that joint).

## Step 4 — Apply and verify

Copy the reviewed file over `bar_bringup_prime/config/prime_calibration.yaml`.
`real.launch.py` folds it into per-joint configs automatically at launch. To verify the
sign end-to-end, fold it, re-launch, and move one joint to a known stop — at the stop,
`/joint_states` should read that joint's URDF limit.

A good cross-check on a symmetric robot: the two arms' offsets should mirror each other
(a joint whose limits are mirrored, like `shoulder_roll`, gets a sign-flipped offset).

## eRob bus-split (hardware-confirmed)

Both arms sit on one EtherCAT ring, 0-based and contiguous. The fifth arm eRob is
`wrist_yaw` (not `wrist_roll`); `wrist_roll` and `wrist_pitch` are the small Sito (CAN)
wrists, not on the eRob chain.

| pos | joint | pos | joint |
|---|---|---|---|
| 0 | left_shoulder_pitch | 5 | right_shoulder_pitch |
| 1 | left_shoulder_roll | 6 | right_shoulder_roll |
| 2 | left_shoulder_yaw | 7 | right_shoulder_yaw |
| 3 | left_elbow_pitch | 8 | right_elbow_pitch |
| 4 | left_wrist_yaw | 9 | right_wrist_yaw |

Waist (positions 10-12) is inferred and not yet verified.

## Gotchas

- **"Limp does nothing / joint stays stiff"** — `0x2383` was not set to 1, so the
  drive ignored the gain writes. `erob_limp_joint.sh` sets it first and the read-back
  shows `Kp=0` when it took.
- **DC is required.** The eRob faults (status `4616`) in free-run CSP; keep DC enabled.
  Damped-limp keeps the drive in CSP/Operation-Enabled the whole time, so this is fine.
- **`wrist_roll`/`wrist_pitch`** are Sito joints — calibrate them with the Sito (CAN)
  procedure, not this one.
