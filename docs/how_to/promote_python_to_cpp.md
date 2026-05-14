---
title: Promote a Python policy to in-process C++
---

# Promote a Python policy to in-process C++

You've trained a policy and validated it through
`bar_policy/remote_policy_runner` (Python) feeding
`RemotePolicyController`. The remote tier crosses a DDS boundary —
add ~1 ms of latency, GIL pauses, harder to debug. For
locomotion-class control rates you want the C++ tier
(`RLPolicyController`) running the same ONNX in-process.

This how-to is the lift-and-shift recipe.

:::info[Status today]
The C++ `RLPolicyController` is **stub-only** at the time of writing
— it loads a `ConstantHoldPolicy` fallback. The schema is real but
the inference layer hasn't been wired to ONNX Runtime C++ yet.
This page documents the intended workflow so it's ready when the
inference path lands; **don't expect a real C++-tier policy run
today**.
:::

## What stays the same

The cross-tier guarantee: **same ONNX file, same metadata schema,
same observation pipeline structurally.** The Python `ObservationManager`
in `bar_policy` mirrors the C++ equivalent (when it ships) term for
term, scale convention for scale convention, joint order for joint
order. A policy debugged in one tier promotes to the other without
re-indexing observations.

Specifically:

| | Python tier | C++ tier |
|---|---|---|
| ONNX file | `~/.cache/bar_policy/wandb/<run>/<file>.onnx` | same file, loaded by `RLPolicyController` |
| Metadata schema | `bar_policy/policy_metadata.py` parses 13 fields | matching C++ parser (TODO) |
| Joint order | reads `joint_names` from metadata | same |
| Observation terms | `term_builders.OBSERVATION_TERM_BUILDERS` | same registry, C++ ports |
| Action scale + default | `PolicyActionDecoder` + `ActionMapper` | same |
| Output | `MITAction` on DDS | direct writes to command interfaces |

## The transition: Python tier → C++ tier

### 1. Validate in Python first

Get the policy fully working with `remote_policy_runner`. Cap the
move at this stage — don't try to debug a new policy in-process. The
Python tier's hot-reload + traceback is much faster for iteration.

### 2. Place the ONNX where the C++ tier can find it

The C++ runner doesn't (yet) integrate with the W&B cache. Copy the
selected `.onnx` to a fixed path in the workspace:

```bash
cp ~/.cache/bar_policy/wandb/<run-id>/model_4000.onnx \
   bar_controllers/config/rl_policy.onnx
```

This file is **per-trained-policy**, not per-physical-robot. Cache
it in `git lfs` if you're versioning checkpoints.

### 3. Update `bar_lite_controllers.yaml`

The placeholder `observation_dim=0 / action_dim=0` config has to be
replaced with real values from your policy's metadata:

```yaml
rl_policy_controller:
  ros__parameters:
    joints: [...]  # same canonical 14-joint order

    # Read these from the ONNX metadata. Don't guess — mismatched dims
    # would make on_configure happily accept the values, and inference
    # would then produce garbage.
    observation_dim: <int from metadata>
    action_dim: <int from metadata>

    default_joint_position: [<from metadata.default_joint_position>]
    action_scale: [<from metadata.action_scale>]
    stiffness: [<from metadata.stiffness>]
    damping: [<from metadata.damping>]

    onnx_path: bar_controllers/config/rl_policy.onnx
    imu_topic: "/imu/data"
    fallback_controllers: ["damping_controller"]
```

### 4. Restore `rl_policy_controller` to the spawner batch

Currently dropped from `real.launch.py`'s `inactive_spawner` because
the placeholder zeros made `on_configure` fail. Once the YAML has
real dims:

```python
# bar_bringup_lite/launch/real.launch.py
inactive_spawner = Node(
    package='controller_manager',
    executable='spawner',
    arguments=[
        'damping_controller',
        'standby_controller',
        'rl_policy_controller',     # ← restore
        'remote_policy_controller',
        '--controller-manager', '/controller_manager',
        '--inactive',
    ],
)
```

### 5. Activate via the FSM, not by hand

The FSM gates the active-policy transitions on `is_finished:true`
from STANDBY. The locomotion path is:

```
DAMP → LOAD → wait for is_finished → START_LOCOMOTION (R1+B on gamepad)
```

Equivalent CLI:

```bash
ros2 control switch_controllers --deactivate zero_torque_controller --activate damping_controller
ros2 control switch_controllers --deactivate damping_controller    --activate standby_controller
# wait for /standby_controller/state.is_finished == true
ros2 control switch_controllers --deactivate standby_controller   --activate rl_policy_controller
```

### 6. Watch the safety pipeline closely on first run

In-process inference has no DDS shield between bad model output and
the wire. If the policy outputs a NaN, the C++ controller's
`update()` should return `ERROR` (catch the NaN in the observation
or action arrays). Verify:

```bash
ros2 topic echo /control_mode
# Watch for status_message changes if rl_policy returns ERROR.
```

`fallback_controllers: ["damping_controller"]` on the policy
controller means a NaN trips back to DAMPING within a tick, but
verify it actually happens before you trust the policy.

## When *not* to promote

- **Manipulation / VLA policies.** These often need PyTorch /
  diffusion / transformer libs that are awkward in C++. Stay
  out-of-process — the latency floor of remote_policy is typically
  fine for manipulation rates (10-100 ms).
- **Hugging Face dataset loaders.** The reference dataset loader in
  `bar_policy/reference/_loader.py` is a minimal-pyarrow reader; it
  doesn't have a C++ equivalent. If your policy needs dataset-driven
  references, stay Python.
- **Policies that are still iterating.** Keep the Python edit-loop
  until the policy is stable.

The C++ tier is specifically for **locomotion-class dynamical
control** where 1 ms matters and inference fits cleanly in
ONNX Runtime.

## See also

- [Reference → Policy runner](../reference/policy_runner.md) — the
  Python side in full detail.
- [Concepts → Frozen schemas](../concepts/frozen_schemas.md) — the
  metadata contract both tiers share.
- The C++ controller skeleton:
  [`bar_controllers/src/rl_policy_controller.cpp`](https://github.com/T-K-233/bar_ros2/blob/main/bar_controllers/src/rl_policy_controller.cpp).
