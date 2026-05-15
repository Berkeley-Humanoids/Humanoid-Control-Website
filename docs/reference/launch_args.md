# Launch args

Every BAR bringup follows the same vocabulary. Each robot ships **two
parallel launches** — `real.launch.py` for silicon, `mujoco.launch.py` for
MuJoCo physics. Operators pick the *launch file* rather than flipping a
`use_fake_hardware` flag on a single one. The xacro still accepts
`use_fake_hardware:=true` for direct ad-hoc visualization, but no
bundled launch enables that path.

## `bar_description_lite/launch/view_lite.launch.py`

URDF inspector — no controller_manager, no physics.

| Arg | Default | Effect |
|---|---|---|
| `rviz_config` | bundled `view_lite.rviz` | Override with your own RViz layout. |

Implicit: forces `use_fake_hardware:=true` on the xacro so the
`<ros2_control>` block is harmless when `robot_state_publisher` parses
the URDF.

## `bar_bringup_lite/launch/real.launch.py`

Real-hardware Lite bringup. Loads **two** `bar_hw_robstride/RobstrideSystem`
instances, one per physical SocketCAN bus (`LiteLeftArm` claims CAN ids
11..17 on the left bus, `LiteRightArm` claims 21..27 on the right bus).

| Arg | Default | Effect |
|---|---|---|
| `can_interface_left`  | `can0` | SocketCAN ifname for the **left arm** block (CAN ids 11..17). |
| `can_interface_right` | `can1` | SocketCAN ifname for the **right arm** block (CAN ids 21..27). |
| `calibration_file`    | `<bar_bringup_lite share>/config/calibration.json` | Absolute path to the per-physical-robot zero-offset JSON. Pass `''` for identity calibration (only the URDF `direction` sign flip applies, no offset). See [Hardware specs → Bus-bring-up checklist](./hardware_specs.md#bus-bring-up-checklist) for how to regenerate. |
| `enable_mode_manager` | `true` | `false` skips spawning the FSM orchestrator. Used by `calibrate.launch.py` and for raw-debug bringups where the operator drives controllers directly via `ros2 control switch_controllers`. |
| `enable_gamepad`      | `false` | `true` spawns `joy_node` so `mode_manager` can read `/joy`. Otherwise keyboard-only (and only when stdin is a TTY). |
| `enable_rerun_viz`    | `false` | `true` spawns the `bar_bringup_lite rerun_viz` Python node — native rerun viewer that subscribes `/robot_description` + `/joint_states` and renders the live kinematic chain. Requires `pip install rerun-sdk`. |
| `enable_viser_viz`    | `false` | `true` spawns the `bar_bringup_lite viser_viz` Python node — browser-based viewer (served at `http://0.0.0.0:8080` by default). Same subscriptions as `rerun_viz`; the two can run simultaneously. Requires `pip install viser yourdfpy 'scipy>=1.13'` (the scipy floor avoids a numpy-2 binary-compat conflict with rerun-sdk). |

The active-policy target is picked by the START button, not a launch
arg: R1+A activates `remote_policy_controller` (out-of-process policy),
R1+B activates `rl_policy_controller` (in-process RL — currently
**not auto-spawned** because its placeholder `observation_dim=0` /
`action_dim=0` config makes `on_configure` fail; load manually with
`ros2 control load_controller` once a real metadata schema lands). See
[Controllers → `mode_manager`](controllers.md#mode_manager-executable).

Implicit on the xacro: `use_fake_hardware:=false use_sim:=false`.

## `bar_bringup_lite/launch/calibrate.launch.py`

Bundles `real.launch.py` with three overrides
(`calibration_file:='' enable_mode_manager:='false' enable_gamepad:='false'`)
and adds the `calibrate_robot` observer node. The plugin runs with identity
calibration so `/joint_states` carries `direction × raw_motor_pos`, which is
the frame the homing-offset formula expects.

| Arg | Default | Effect |
|---|---|---|
| `can_interface_left`  | `can0` | Forwarded to `real.launch.py`. |
| `can_interface_right` | `can1` | Forwarded to `real.launch.py`. |
| `output` | `$PWD/calibration.json` | Path the calibration observer writes on Ctrl+C. After verifying, `mv` it over `bar_bringup_lite/config/calibration.json` to make it the default for the next `real.launch.py`. |
| `sweep_threshold` | `0.5` | Minimum joint sweep (rad) below which the prior `homing_offset` is preserved instead of recomputed. Lets you re-calibrate one or two joints at a time without losing the others. |

The observer reads per-joint static config (`direction`, `lower_limit`,
`upper_limit`, `can_id`) from `/robot_description` — there's no parallel
YAML config for it to drift against. Output JSON schema is byte-for-byte
compatible with
[`T-K-233/Lite-Lowlevel-Python`](https://github.com/T-K-233/Lite-Lowlevel-Python)'s
`calibration.json`.

## `bar_bringup_lite/launch/mujoco.launch.py`

MuJoCo Lite bringup. Loads `mujoco_ros2_control/MujocoSystem` inside the
`mujoco_sim` process (which hosts the controller_manager as a physics
plugin).

| Arg | Default | Effect |
|---|---|---|
| `scene` | `lite` | MJCF scene name. **`lite`** loads `bar_description_lite/mjcf/lite.xml` (robot only). **`lite_piano`** composes a runtime scene XML that `<include>`s the robot MJCF and `bar_piano/mjcf/piano.xml` (positioned per Pianist's `UdeDummyCfg`). Any other name is treated as `bar_description_lite/mjcf/<name>.xml`, so you can drop a static scene XML in that directory and select it without editing the launch file. |
| `enable_gamepad` | `false` | Same as the real bringup. |

Implicit:

- The xacro is invoked with `use_sim:=true`. **`use_sim` wins over
  `use_fake_hardware`** in the xacro's `<plugin>` selector — see the
  decision tree in [Packages](packages.md#bar_description_lite--bar_description_prime).
- Every node runs with `use_sim_time:=true`. Time advances at MuJoCo's
  pace via `/clock`.
- `bar_bringup_lite/config/sim_overrides.yaml` is layered on top of
  `bar_controllers/config/bar_lite_controllers.yaml` so the real-hardware
  launch stays sim-time-free.
- `scene:=lite_piano` writes the composed scene into
  `<bar_description_lite share>/mjcf/_runtime_lite_piano.xml` so MuJoCo's
  root-file-relative path resolution still finds the robot meshes via
  `meshdir="../meshes/"`. The launch passes the absolute path to
  `mujoco_sim` (which we patched to skip the `<package_share>/<rel>`
  join when `model_file` is absolute).

## `bar_bringup_prime/launch/real.launch.py`

Real-hardware Prime bringup. Loads both `ethercat_driver/EthercatDriver`
(eRob arms) and `bar_hw_sito/SitoSystem` (auxiliary) — two concurrent
`<ros2_control>` blocks in the URDF.

| Arg | Default | Effect |
|---|---|---|
| `can_interface` | `can0` | Sito side. |
| `ethercat_iface` | `eth0` | EtherCAT NIC. Consumed by `ethercat_driver_ros2`. |
| `enable_gamepad` | `false` | Same as Lite. |

The Prime URDF is **not yet imported** from CAD — this launch will not
fully wire controllers until that lands.

## `bar_bringup_prime/launch/mujoco.launch.py`

Mirrors `bar_bringup_lite/mujoco.launch.py` for Prime. Same `enable_gamepad`
arg, same xacro selection (`use_sim:=true`), same `sim_overrides.yaml`
overlay pattern. Loads the Prime URDF instead of Lite's.

## xacro args (`bar_description_lite/urdf/lite.urdf.xacro`)

The launch args ultimately feed these xacro args. Useful when driving
xacro directly (e.g. in a sim2sim eval harness):

| Arg | Default | Effect |
|---|---|---|
| `use_fake_hardware` | `true` | Select `mock_components/GenericSystem` — single combined `<ros2_control>` block. Only the **xacro layer** exposes this; no bundled launch uses it today. |
| `use_sim` | `false` | **Wins over `use_fake_hardware`** — select `mujoco_ros2_control/MujocoSystem`, also single combined block. |
| `can_interface_left`  | `can0` | Emitted as a system-level `<param>` on the `LiteLeftArm` block only on the real-hardware path. |
| `can_interface_right` | `can1` | Same, for `LiteRightArm`. |
| `calibration_file`    | `""`   | Passed verbatim as a `<param name="calibration_file">` on both real-hardware blocks. Empty = identity calibration. |

## Common combinations

```sh
# Drag joints in RViz, no controllers.
ros2 launch bar_description_lite view_lite.launch.py

# MuJoCo physics, /clock from sim time.
ros2 launch bar_bringup_lite mujoco.launch.py

# MuJoCo physics with the portable piano in front of the robot.
ros2 launch bar_bringup_lite mujoco.launch.py scene:=lite_piano

# Real Lite, both buses, gamepad. Press R1+A at STANDBY to start the remote policy.
ros2 launch bar_bringup_lite real.launch.py \
    can_interface_left:=can0 \
    can_interface_right:=can1 \
    enable_gamepad:=true

# Calibrate the zero pose (writes ./calibration.json on Ctrl+C).
ros2 launch bar_bringup_lite calibrate.launch.py
```
