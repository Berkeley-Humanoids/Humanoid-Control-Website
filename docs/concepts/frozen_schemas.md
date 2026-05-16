---
title: Frozen schemas
---

# Frozen schemas

A few things in `bar_ros2` are described as **frozen**. This page
explains which ones, why, and what to do when you want to change them.

![Frozen schemas and their consumers](/img/diagrams/concepts__frozen_schemas__01.svg)

## What "frozen" means

A schema is frozen when **changing it requires retraining (or
re-trainable replacement of) any policy that depends on it**. The
moment a trained ONNX file has been generated against the schema,
the schema's contract is binding for that file. Changing it silently
produces wrong outputs.

The point of marking schemas as frozen is to make this contract
explicit so a reviewer in six months knows "if I add a joint here,
I have to retrain". It also tells the rest of the project where the
risk lives — most of the codebase is fine to refactor; these
specific surfaces are not.

## What's frozen

### 1. Canonical joint order

The order of joints in `bar_lite_controllers.yaml`'s `joints:` list
is canonical:

```yaml
joints:
  - left_shoulder_pitch
  - left_shoulder_roll
  - left_shoulder_yaw
  - left_elbow_pitch
  - left_wrist_yaw
  - left_wrist_roll
  - left_wrist_pitch
  - right_shoulder_pitch
  ...
```

Every consumer that needs an index — the C++ `MITState` struct, the
Python `ObservationManager`, the `MITAction` message's parallel
arrays, the ONNX policy's input vector — refers to **this order by
index**. Reordering means every policy's input layer wires to the
wrong joint.

When to extend: appending a new joint at the end (e.g. the neck) is
safe — old policies that consume only the first N entries still
work. Inserting or reordering is not safe.

### 2. `bar_msgs/MITAction` fields

The on-wire command format between `bar_policy/remote_policy_runner`
and `RemotePolicyController`:

```
std_msgs/Header   header
string[]          joint_names
float64[]         position
float64[]         velocity
float64[]         effort
float64[]         stiffness
float64[]         damping
```

Five parallel arrays + names. The arrays are indexed in the same
canonical joint order above. Adding a field breaks parsers; renaming
a field breaks everything.

### 3. The 5 MIT command interface names

```
position, velocity, effort, stiffness, damping
```

These names are not arbitrary — they match
`mujoco_ros2_control::MujocoSystem`'s `HW_IF_STIFFNESS = "stiffness"`
/ `HW_IF_DAMPING = "damping"` constants exactly. Renaming
`stiffness` to e.g. `kp` would break the binding against the sim
plugin while leaving the silicon plugin happy — silent skew.

### 4. The ONNX `custom_metadata_map` schema (`bar_policy`)

`bar_policy/policy_metadata.py` parses 13 fields baked into every
trained `.onnx`:

```
joint_names, default_joint_position, action_scale,
stiffness, damping, observation_terms, body_names,
dataset_repo_id, policy_dt, ...
```

These are the **deployment contract** of the policy. If training
forgets to bake one of them in, the runner refuses to load the
checkpoint — there is no YAML fallback, by design. Adding a field
requires both training-side and runner-side support, in lockstep.

### 5. `SafetyStatus.flags` bit positions

```
FLAG_BUS_OFF             = 1 << 0
FLAG_RX_TIMEOUT          = 1 << 1
FLAG_TX_QUEUE_OVERRUN    = 1 << 2
FLAG_MOTOR_FAULT         = 1 << 3
FLAG_TEMPERATURE_LIMIT   = 1 << 4
FLAG_INVALID_FRAME       = 1 << 5
```

The bit positions can't be renumbered without a recorded-bag
compatibility break. Adding new bits is fine (use the next free
position); removing them is not.

## What's NOT frozen

To draw the contrast: most of the rest of the project is free to
refactor.

- **Per-joint default `K_p` / `K_d`** in `bar_lite_controllers.yaml`
  are tuning numbers, not schema. Change at will.
- **CAN ids in the URDF** are wiring facts; if the physical robot
  changes, the URDF changes.
- **`calibration.json` values** are per-physical-robot;
  regenerating them is the *normal case*, not a schema change.
- **Internal C++ field names** in the plugin / controller classes —
  refactor freely.
- **The set of available controllers** — adding a new mode-FSM
  member is a versioned change, not a freeze. (Removing one is
  more delicate: any policy that ran against the old controller
  may have been validated against its specific behavior.)

## How to change a frozen schema

The drill, in order:

1. **Write down what depends on it.** Every trained policy, every
   subscriber, every rosbag from the past.
2. **Stage the change** — branch + commit + describe in the PR
   exactly which schemas move and why.
3. **Bump a version**. For `bar_msgs`, that's the message's
   `package.xml` version + a deprecation period (parallel old +
   new field, or a v2 message type, for at least one release).
4. **Retrain every trained policy** against the new schema.
   Document the (old → new) mapping for anyone whose checkpoint
   isn't being retrained.
5. **Land everything together.** A half-landed schema change is the
   silent-skew failure mode — old policy loading against new
   message types and silently mis-indexing.

For the canonical joint order specifically, the easiest "safe"
change is **appending at the end**. Old policies that consume only
the first N entries continue to work; new policies that consume
N+1+ entries pick up the additions. The neck is the obvious example
— when its actuators land, indices 14–16 are reserved for
`neck_yaw` / `neck_roll` / `neck_pitch`.

## See also

- [Reference → Messages](../reference/messages.md) — the
  field-by-field schemas.
- [Reference → Policy runner](../reference/policy_runner.md) — the
  ONNX `custom_metadata_map` reader.
- The AGENTS.md "Custom interfaces" section in the project root
  states the freezing rule.
