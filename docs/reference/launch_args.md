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

Real-hardware Lite bringup. Loads `bar_hw_robstride/RobstrideSystem` on
the configured SocketCAN bus.

| Arg | Default | Effect |
|---|---|---|
| `can_interface` | `can0` | SocketCAN ifname for the bus library. |
| `enable_gamepad` | `false` | `true` spawns `joy_node` so `mode_manager` can read `/joy`. Otherwise keyboard-only (and only when stdin is a TTY). |

The active-policy target is picked by the START button, not a launch
arg: R1+A activates `remote_policy_controller` (out-of-process policy),
R1+B activates `rl_policy_controller` (in-process RL). See
[Controllers → `mode_manager`](controllers.md#mode_manager-executable).

Implicit on the xacro: `use_fake_hardware:=false use_sim:=false`.

## `bar_bringup_lite/launch/mujoco.launch.py`

MuJoCo Lite bringup. Loads `mujoco_ros2_control/MujocoSystem` inside the
`mujoco_sim` process (which hosts the controller_manager as a physics
plugin).

| Arg | Default | Effect |
|---|---|---|
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
| `use_fake_hardware` | `true` | Select `mock_components/GenericSystem` — only the **xacro layer** exposes this; no bundled launch uses it today. |
| `use_sim` | `false` | **Wins over `use_fake_hardware`** — select `mujoco_ros2_control/MujocoSystem`. |
| `can_interface` | `can0` | Emitted as a system-level `<param>` only when neither `use_sim` nor `use_fake_hardware` is true. |

## Common combinations

```sh
# Drag joints in RViz, no controllers.
ros2 launch bar_description_lite view_lite.launch.py

# MuJoCo physics, /clock from sim time.
ros2 launch bar_bringup_lite mujoco.launch.py

# Real Lite, can0, gamepad. Press R1+A at STANDBY to start the remote policy.
ros2 launch bar_bringup_lite real.launch.py \
    can_interface:=can0 \
    enable_gamepad:=true
```
