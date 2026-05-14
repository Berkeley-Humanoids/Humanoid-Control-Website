---
title: Run a tracking policy
sidebar_position: 3
---

# Tutorial: Run a tracking policy

End-to-end: take a trained ONNX tracking policy, run it through
`bar_policy/remote_policy_runner`, and watch the arms follow a
LeRobot teleop dataset under MuJoCo physics. By the end you'll
know what the runner reads from where, how the metadata schema
makes everything self-describing, and how to swap in your own
policy without rewriting any YAML.

## Time + materials

- 20 minutes
- A working workspace build
- One of: a local `.onnx` checkpoint, OR W&B credentials with access
  to a tracking run, OR access to the canonical Lite-tracking
  checkpoint (see [policy_runner reference](../reference/policy_runner.md)
  for the resolution path)
- Network access for the first run (pulls the LeRobot dataset from
  the HF Hub if you're using the W&B path)

## The mental model

Three actors and the data between them:

```
                   ┌──────────────────────┐
                   │ remote_policy_runner │   (Python, bar_policy)
                   │   - load ONNX         │
                   │   - read 13 metadata  │
                   │     fields            │
                   │   - subscribe /joint_ │
                   │     states + /imu     │
                   │   - step inference @  │
                   │     policy_dt         │
                   └──────────┬───────────┘
                              │ /remote_policy_controller/command
                              │ (bar_msgs/MITAction)
                              ▼
                   ┌──────────────────────┐
                   │ RemotePolicyController│  (C++, bar_controllers)
                   │   - validate joint    │
                   │     order             │
                   │   - hand off via      │
                   │     RealtimeBuffer    │
                   └──────────┬───────────┘
                              │ 5 MIT command interfaces per joint
                              ▼
                   ┌──────────────────────┐
                   │ MujocoSystem          │  (or RobstrideSystem)
                   │   - apply τ = K·err   │
                   │     + D·erṙ + ff      │
                   └──────────────────────┘
```

The policy itself is **self-describing**: every constant it needs
(joint order, K_p, K_d, default pose, action scale, observation
terms, dataset id, tick rate) is baked into the ONNX's
`custom_metadata_map`. You don't write any of this into YAML.

## Step 1 — Bring up MuJoCo

The same launch as the previous tutorial, no gamepad needed:

```bash
ros2 launch bar_bringup_lite mujoco.launch.py
```

Wait for `zero_torque_controller` to come active.

## Step 2 — Walk to STANDBY

`remote_policy_controller` expects the arms in a sane starting pose.
Walk the FSM:

```bash
# Either via the gamepad if you have one:
#   X  → DAMPING
#   L1+A → STANDBY (wait ~4 s for is_finished:true)
#
# Or via direct switch_controllers:
ros2 control switch_controllers --deactivate zero_torque_controller --activate damping_controller
ros2 control switch_controllers --deactivate damping_controller    --activate standby_controller

# Wait for is_finished:
ros2 topic echo /standby_controller/state
# ... is_finished: true
```

## Step 3 — Start the policy runner

In a third terminal:

```bash
# Option (a): local ONNX
ros2 launch bar_policy lite_tracking.launch.py \
    checkpoint:=/path/to/policy.onnx

# Option (b): W&B run path (downloads + caches to ~/.cache/bar_policy/wandb/)
ros2 launch bar_policy lite_tracking.launch.py \
    wandb_run_path:=IsaacLab-Training/mjlab/<run_id>

# Option (c): W&B run with a specific checkpoint pinned
ros2 launch bar_policy lite_tracking.launch.py \
    wandb_run_path:=IsaacLab-Training/mjlab/<run_id> \
    wandb_checkpoint_name:=model_4000.onnx
```

What happens behind the scenes:

1. `checkpoint_loader.resolve_checkpoint` resolves the checkpoint
   to a local file (downloading from W&B if needed, ~1 s once
   cached).
2. The runner parses the ONNX `custom_metadata_map`. You'll see
   logs like:
   ```
   [remote_policy_runner]: joint_names=[14 entries]
   [remote_policy_runner]: policy_dt=0.02  (50 Hz)
   [remote_policy_runner]: observation terms: joint_pos, joint_vel, actions, imu_quat, ref_body_pos, ...
   [remote_policy_runner]: dataset_repo_id=Berkeley-Humanoids/lite-teleop
   ```
3. The runner pulls the LeRobot teleop dataset (parquet shards
   from HF Hub).
4. The runner subscribes to `/joint_states` and (if the observation
   needs it) `/imu/data`.
5. The runner starts a 50 Hz timer; each tick it packs observation,
   runs ONNX inference, decodes the action, builds an `MITAction`,
   and publishes.

At this point the runner is publishing to
`/remote_policy_controller/command` but `remote_policy_controller`
isn't active yet, so nothing changes physically.

## Step 4 — STANDBY → REMOTE

```bash
ros2 control switch_controllers \
    --deactivate standby_controller \
    --activate   remote_policy_controller
```

The motors immediately track the policy. In MuJoCo you'll see the
arms move through the tracking dataset.

Verify the publish rate:

```bash
ros2 topic hz /remote_policy_controller/command
# average rate: 50.0
```

If the runner crashes or the dataset finishes, the stale-command
policy kicks in within 100 ms and the arms go limp. If the runner
is healthy but the rate drops below ~10 Hz, the controller will
also flag stale.

## Step 5 — Inspect the data flow

```bash
# What does an MITAction actually look like?
ros2 topic echo --once /remote_policy_controller/command | head -30

# How fast is observation packing?
ros2 topic hz /joint_states           # 50 Hz from the broadcaster
ros2 topic hz /remote_policy_controller/command   # 50 Hz from the runner
```

The two rates match because the runner ticks at `policy_dt = 0.02`,
which equals the controller_manager's update rate.

## Step 6 — Shut down

DAMP first, then exit:

```bash
ros2 control switch_controllers \
    --deactivate remote_policy_controller \
    --activate   damping_controller

# Kill the runner first (Ctrl+C in its terminal), then the launch.
```

The runner's `finally` clause closes the publishers cleanly; the
launch's `on_deactivate` cascades through controllers.

## What you came away with

| Skill | Page where it's documented in detail |
|---|---|
| Resolving an ONNX checkpoint (local / W&B) | [Reference → Policy runner](../reference/policy_runner.md) |
| The 13 metadata fields | same |
| LeRobot dataset path | same |
| The `MITAction` schema | [Reference → Messages](../reference/messages.md) |
| `RemotePolicyController` lifecycle | [Reference → Controllers](../reference/controllers.md#barremotepolicycontroller) |

## Next

- [How-to → Promote a Python policy to in-process C++](../how_to/promote_python_to_cpp.md)
  — the lower-latency path, once you've validated in Python.
- [Concepts → Frozen schemas](../concepts/frozen_schemas.md) — what
  about this contract is frozen, and what's tunable.
