# Policy runner

`bar_policy.remote_policy_runner` is the Python `rclpy` node that drives
`bar::RemotePolicyController` from an ONNX policy + (optionally) a LeRobot
reference dataset. This page documents the launch surface, the ONNX
metadata schema the runner reads, and the observation-term registry that
maps names from the ONNX to `ObservationTerm` instances.

## Why "self-describing ONNX"

The training pipeline writes 13 fields into the ONNX file's
`custom_metadata_map` at export time — joint order, per-joint PD gains,
default pose, action scale, observation term names, body names, the
LeRobot dataset id, the policy tick period. The runner parses those
fields into a typed `PolicyMetadata` object and never relies on YAML to
restate them.

This matters because **any mismatch between the training-time graph and
the deployment-time YAML breaks the policy silently** (wrong joint order
or off-by-one observation slice will still produce well-shaped tensors
that just behave terribly). Embedding the metadata in the ONNX file means
training and deployment cannot drift independently.

## Composition

| Module | Responsibility |
|---|---|
| `OnnxPolicyRunner` | `onnxruntime.InferenceSession` wrapper. Single-step inference, shape contract `float32 (1, N) -> float32 (1, M)`. |
| `PolicyMetadata` | Frozen dataclass decoded from `custom_metadata_map`. Helpers like `joint_stiffness_map()`, `default_joint_pos_map()`, `action_scale_map()` return `dict[str, float]` keyed by joint name. |
| `term_builders.build_observation_terms` | Resolves each name in `observation_names` to an `ObservationTerm` via three-stage lookup: built-in proprioception → reference-provider term → constant fallback. Unknown names raise. |
| `ObservationManager` | Concatenates configured terms into the policy input vector each tick. Owns the reference-provider lifecycle (`reset` on activation, `step` after each `record_action`). |
| `TrackingReferenceProvider` | Loads a LeRobot dataset (local path or HF repo id) and serves per-frame body-pos / body-ori / joint references on the manager's cadence. Mirrors the training-side `pianist_tracking.loader.teleop_sequence` layout exactly. |
| `PolicyActionDecoder` | `target[name] = default[name] + action[name] * scale[name]`. |
| `ActionMapper` | Assembles a full-articulation `MITAction` from any `{joint_name: target_position}` map. Undriven joints (those not in `action_joint_names`) are pinned to `position=0` with the same `K`/`D` the policy ships, so the controller never holds an arbitrary pose. |

## ONNX metadata schema

The 13 required keys (parsed from `session.get_modelmeta().custom_metadata_map`):

| Key | Type | Meaning |
|---|---|---|
| `task_type` | `"tracking"` \| `"piano"` \| `"locomotion"` | Selects the reference provider class. |
| `joint_names` | `tuple[str, ...]` | Full articulation list (17 for Lite). Indexes `joint_stiffness`, `joint_damping`, `default_joint_pos`. |
| `action_joint_names` | `tuple[str, ...]` | The subset the policy actually emits actions for. Joints in `joint_names` but not here are "undriven" and get pinned to zero. |
| `joint_stiffness` | `tuple[float, ...]` | Per-joint `K_p`, aligned to `joint_names`. |
| `joint_damping` | `tuple[float, ...]` | Per-joint `K_d`, aligned to `joint_names`. |
| `default_joint_pos` | `tuple[float, ...]` | Per-joint default position (the `q_default` in `out = (q - q_default) * scale`). |
| `observation_names` | `tuple[str, ...]` | The flat observation vector, term by term. See [Observation term registry](#observation-term-registry). |
| `command_names` | `tuple[str, ...]` | Future-use; runtime command terms (e.g. velocity targets) that aren't part of the proprio observation. |
| `action_scale` | `float` \| `tuple[float, ...]` | Per-action-joint scale. Scalar broadcasts across all joints. |
| `policy_dt` | `float` | Policy tick period in seconds. The runner uses this for its `create_timer` unless `policy_dt_override` is set. |
| `body_names` | `tuple[str, ...]` | Reference-tracked bodies (for `ref_body_pos` / `ref_body_ori` terms). |
| `dataset_repo_id` | `str` | Default HF repo id for the reference dataset; overridable at launch. |
| `lookahead_steps` | `tuple[int, ...]` | Piano-only: frame offsets the policy was trained to look ahead at. |

## Observation term registry

`observation_names` is a CSV like
`ref_body_pos, ref_body_ori, joint_pos, joint_vel, actions`. Each name
maps to one of three sources, resolved in this order:

1. **Built-in proprioception terms** — instantiated directly from the
   metadata:

   | Name | Term class | Slice from |
   |---|---|---|
   | `joint_pos` | `JointPositionTerm(default, scale=1)` | `state.joint_position - default` |
   | `joint_vel` | `JointVelocityTerm(num_joints, scale=1)` | `state.joint_velocity` |
   | `actions` | `LastActionTerm(action_dim)` | last action recorded via `record_action()` |
   | `imu_quaternion` | `ImuFieldTerm("imu_quaternion")` | `state.imu_quat` `(w, x, y, z)` |
   | `imu_angular_velocity` | `ImuFieldTerm(...)` | `state.imu_gyro` |
   | `imu_linear_acceleration` | `ImuFieldTerm(...)` | `state.imu_accel` |

2. **Reference-provider terms** — delegated to the attached provider
   (today only `TrackingReferenceProvider`). The provider declares its
   own supported terms via `supports(name)`; tracking provides
   `ref_body_pos`, `ref_body_ori`, `ref_joint_pos`.

3. **Constant terms** — caller-supplied fallback. Useful for running
   without a dataset (zero-fill `ref_body_pos`) during smoke tests.

Unknown names raise `ValueError` at runner startup — the build-time
guarantee is that **every observation slot has a deterministic source**.

## Launch parameters

`remote_policy_runner` (entry point: `remote_policy_runner =
bar_policy.remote_policy_runner:main`):

| Param | Default | Effect |
|---|---|---|
| `checkpoint` | (required) | Path to the `.onnx` file. Raises if empty. |
| `dataset` | `''` | Explicit **local** LeRobot directory. Wins over both override and metadata. |
| `dataset_repo_id_override` | `''` | HF repo id to use instead of the ONNX-baked one. Useful when iterating on dataset variants. |
| `episode_index` | `-1` | Specific episode to track; `-1` lets the provider pick (first episode). |
| `command_topic` | `/remote_policy_controller/command` | Where to publish `MITAction`. Must match `RemotePolicyController`'s subscription. |
| `joint_state_topic` | `/joint_states` | Source for proprio state (driven by `joint_state_broadcaster`). |
| `policy_dt_override` | `0.0` | Force a different tick period than `PolicyMetadata.policy_dt`. `0.0` means use metadata. |

## Dataset resolution order

The runner picks the reference dataset source in this priority:

1. **`dataset:=<local path>`** — air-gapped deployments pre-fetch via
   `hf download` and point here.
2. **`dataset_repo_id_override:=<hf_repo_id>`** — for testing alternative
   datasets without re-exporting the ONNX.
3. **`PolicyMetadata.dataset_repo_id`** — the default. First run will
   download from Hugging Face Hub.

Logged at startup so you always know which one was used.

## Per-tick flow

Each timer fire (at `policy_dt`):

1. Build the observation: every `ObservationTerm.pack(state, slice)` runs
   against the current `MITState` (refreshed from `/joint_states`) and
   the current reference frame (from the provider).
2. Run the ONNX forward pass on the flat observation vector.
3. Decode the raw action via
   `target[name] = default[name] + action[name] * scale[name]`.
4. Assemble the `MITAction` with the configured `K_p` / `K_d` and undriven
   joints pinned to `position=0`.
5. Publish on `command_topic`.
6. `obs_mgr.record_action(action)` — refreshes `LastActionTerm` and steps
   the reference provider so the dataset frame advances exactly once.

Steps 5 and 6 are intentionally ordered so the policy never observes the
*post-action* dataset frame on the same tick it commanded against — every
tick is `(t, t+1)` in the dataset, never `(t+1, t+1)`.

## See also

- [`bar/RemotePolicyController`](controllers.md#barremotepolicycontroller)
  — the controller-side half of this pipeline.
- [Architecture: Two parallel policy tiers](../concepts/architecture.md#two-parallel-policy-tiers)
  — how the in-process and out-of-process tiers relate.
