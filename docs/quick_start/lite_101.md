# bar_ros2 101 — Lite walkthrough

A 30-minute hands-on tour. We'll go from "URDF loaded in RViz" to "MuJoCo
simulation with all five mode controllers spawned", explaining what's happening
behind each command.

Prerequisites: a built workspace, [from the previous page](installation.md).

```sh
cd ~/bar_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

## Step 1 — Visualize the URDF

The simplest possible launch: a `robot_state_publisher` + a
`joint_state_publisher_gui` + RViz. No physics, no `ros2_control` — just the
kinematic chain.

```sh
ros2 launch bar_description_lite view_lite.launch.py
```

What you'll see:

- **RViz** loads with the chest at world origin and arms at zero pose.
- A **slider panel** (jsp_gui) appears with one slider per actuated joint.
- Dragging a slider should make the corresponding link rotate in RViz.

:::tip["What is xacro doing?"]
The `.xacro` file is a Jinja-ish macro language for URDFs. Our top-level
`lite.urdf.xacro` includes `lite.ros2_control.xacro`, which selects the
`<plugin>` based on the `use_sim` / `use_fake_hardware` args. For visualization
we force `use_fake_hardware:=true` so the `<ros2_control>` block is harmless
(mock_components, which never gets loaded here anyway because RViz doesn't
spawn the controller_manager).
:::

## Step 2 — MuJoCo bringup

Now bring up the full control plane against MuJoCo physics:
`controller_manager` hosted inside `mujoco_sim`, all five mode-FSM
controllers, and the `mode_manager` orchestrator. Nothing on the bus —
the `MujocoSystem` hardware plugin writes the same MIT-mode torque
formula to `qfrc_applied` that our Robstride firmware computes on real
hardware.

```sh
ros2 launch bar_bringup_lite mujoco.launch.py
```

A **MuJoCo viewer window** appears with the Lite humanoid at zero pose.
The single `mujoco_sim` process hosts MuJoCo physics, the
`MujocoRos2ControlPlugin` (loaded as a pluginlib physics plugin), the
`controller_manager` inside that, and the `MujocoSystem` hardware
interface inside that. From the controller's point of view nothing
distinguishes this from real hardware — the same 5 command interfaces
and 3 state interfaces are exported.

![flowchart LR](/img/diagrams/quick_start__lite_101__04.svg)

Wait ~2 seconds, then in a second terminal:

```sh
source ~/bar_ws/install/setup.bash
ros2 control list_controllers
```

Expected output:

```
joint_state_broadcaster   joint_state_broadcaster/JointStateBroadcaster   active
zero_torque_controller    bar/ZeroTorqueController                        active
damping_controller        bar/DampingController                           inactive
standby_controller        bar/StandbyController                           inactive
rl_policy_controller      bar/RLPolicyController                          inactive
remote_policy_controller  bar/RemotePolicyController                      inactive
```

### What just happened

![sequenceDiagram](/img/diagrams/quick_start__lite_101__02.svg)

`zero_torque_controller` is active as the **safe startup default**: it claims
all 5 command interfaces on every joint and writes `0` to all of them, every
tick. From an operator's perspective the robot is "alive but inert".

### Watch the topics

```sh
ros2 topic list | grep -E "joint_states|control_mode|standby|safety"
# /control_mode
# /joint_states
# /safety_status
# /standby_controller/state
```

`joint_state_broadcaster` publishes `/joint_states` at the controller_manager's
update rate (50 Hz):

```sh
ros2 topic hz /joint_states
# average rate: 50.000
```

`mode_manager` publishes `/control_mode` (the current FSM state) at the same
rate:

```sh
ros2 topic echo --once /control_mode
# header:
#   stamp: ...
#   frame_id: ''
# mode: 0           # ZERO_TORQUE
# controller_name: zero_torque_controller
# status_message: ''
```

## Step 3 — Trigger a mode transition

Press `Ctrl+C` in the launch terminal — wait, **don't do that**. That tears
down the launch. Instead, send the `DAMP` intent.

`mode_manager` accepts intents from `/joy` (USB gamepad) or, when stdin is a
TTY, raw keyboard via `termios`. The launch we ran does not have `stdin`
attached to mode_manager (it was started from a `ros2 launch` Python
ExecuteProcess); for now we'll just call the controller_manager service
directly to simulate what `mode_manager` would have done:

```sh
ros2 control switch_controllers \
    --activate damping_controller \
    --deactivate zero_torque_controller
```

Re-check:

```sh
ros2 control list_controllers
# damping_controller        bar/DampingController                           active
# zero_torque_controller    bar/ZeroTorqueController                        inactive
```

### Inspect the command stream

```sh
ros2 topic echo --once /dynamic_joint_states
# Should show stiffness=0, damping=1.0, position_cmd ~= current position
```

:::tip[Why DAMPING is the "compliant fail-safe"]
With stiffness `K = 0` there's no position-restoring force. With damping `D`
nonzero the joint resists velocity. The result: the robot is **soft under
gravity** (you can push the arm and it moves) but **damped** (it doesn't
oscillate). This is the state you switch into before powering down, before
swapping a tool, or after any non-OK SafetyStatus.
:::

## Step 4 — Confirm physics is actually advancing

The MuJoCo viewer's apparent stillness can be deceiving — confirm
physics is ticking and joint state is flowing:

```sh
ros2 topic hz /clock                 # MuJoCo physics time
ros2 topic echo --once /joint_states # actual positions from mjData->qpos
ros2 control list_controllers        # same 6 controllers
```

If gravity is on (default MJCF), and you switch to DAMPING, the arms should
**sag slightly** under gravity — the damping resists fall velocity but the
zero stiffness can't hold them up.

### Send a fake VLA command

`remote_policy_controller` is loaded inactive. Activate it:

```sh
ros2 control switch_controllers \
    --activate remote_policy_controller \
    --deactivate zero_torque_controller
```

Now publish a `MITAction` to it (this is what `bar_policy` would do):

```sh
ros2 topic pub --once /remote_policy_controller/command \
    bar_msgs/msg/MITAction \
    "{header: {stamp: now},
      joint_names: ['left_shoulder_pitch', 'left_shoulder_roll', 'left_shoulder_yaw',
                    'left_elbow_pitch', 'left_wrist_yaw', 'left_wrist_roll', 'left_wrist_pitch',
                    'right_shoulder_pitch', 'right_shoulder_roll', 'right_shoulder_yaw',
                    'right_elbow_pitch', 'right_wrist_yaw', 'right_wrist_roll', 'right_wrist_pitch',
                    'neck_yaw', 'neck_roll', 'neck_pitch'],
      position: [0.0, 0.5, 0, -0.5, 0, 0, 0,
                 0.0, -0.5, 0, -0.5, 0, 0, 0,
                 0, 0, 0],
      velocity: [0,0,0,0,0,0,0, 0,0,0,0,0,0,0, 0,0,0],
      effort:   [0,0,0,0,0,0,0, 0,0,0,0,0,0,0, 0,0,0],
      stiffness:[50,50,50,50,50,50,50, 50,50,50,50,50,50,50, 30,30,30],
      damping:  [2,2,2,2,2,2,2, 2,2,2,2,2,2,2, 1,1,1]}"
```

Both arms should bend their shoulder_roll and elbow_pitch joints.

:::tip[Stale-command behavior]
After 100 ms with no new `MITAction`,
`remote_policy_controller` falls into its **stale policy**. The default is
`passive` — write zero stiffness/damping — which makes the arms go limp.
With `stale_command_policy: hold`, it holds the last command indefinitely.
:::

## Step 5 — Use a real gamepad (optional)

If you have a USB gamepad plugged in:

```sh
# Re-launch with gamepad enabled
ros2 launch bar_bringup_lite mujoco.launch.py \
    enable_gamepad:=true
```

Now intents map to buttons. The **two `START_*` intents are
distinguished by which face button you press**, not by a launch arg —
operators pick the policy target at runtime:

| Intent | Gamepad | Effect |
|---|---|---|
| `DAMP` | `X` | → DAMPING (admissible from any state) |
| `LOAD` | `L1+A` **or** `L1+B` | DAMPING → STANDBY |
| `START_REMOTE` | `R1+A` | STANDBY → REMOTE (gated on `is_finished`) |
| `START_LOCOMOTION` | `R1+B` | STANDBY → LOCOMOTION (gated on `is_finished`) |
| `QUIT` | `BACK` | exit from ZERO_TORQUE or DAMPING only |

A keyboard reader is declared but not yet implemented — see
[Controllers → `mode_manager`](../reference/controllers.md#mode_manager-executable)
for the joy button indices and how to remap them via launch params.

## What you've just seen

In ~30 minutes you've exercised three of the project's main axes:

The **fourth axis** — robot (Lite vs. Prime) — gets exercised by swapping
`bar_bringup_lite` for `bar_bringup_prime`. Same controllers, same FSM, just a
different URDF and a different hardware plugin.

## Next

- [Packages reference](../reference/packages.md) — what's in each package.
- [Controllers reference](../reference/controllers.md) — per-controller
  parameters and tuning notes.
- [Software framework](../overview/software_framework.md) — deeper dive into
  the FSM and policy tiers if you skipped the overview.