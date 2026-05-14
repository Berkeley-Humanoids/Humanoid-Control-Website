# Lite 101

A 20-minute hands-on lesson. You'll go from "URDF loaded in RViz" to "the
full controller stack running in MuJoCo, with a controller switch under
your fingers". By the end you'll recognise the four moving pieces of the
project — the URDF, the controller_manager, the mode-FSM controllers, and
the simulation backend — and be ready to read the rest of the docs with
that mental model in place.

:::tip[This is a tutorial, not a how-to]
The aim here is **learning by doing**, not "production realism". For
calibrating a real robot, recovering from a fault, or wiring a gamepad,
look in [How-to guides](../how_to/index.md) once those land. For the
why-behind-the-what, [Concepts](../concepts/index.md).
:::

Prerequisites: a built workspace, from the [previous page](./installation.md).

```sh
cd ~/bar_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

## Step 1 — Visualize the URDF

The simplest possible launch: `robot_state_publisher` + a
`joint_state_publisher_gui` + RViz. No physics, no `ros2_control` — just
the kinematic chain.

```sh
ros2 launch bar_description_lite view_lite.launch.py
```

What you'll see:

- **RViz** opens with the chest at world origin and the arms hanging at
  zero pose.
- A **slider panel** (jsp_gui) appears with one slider per actuated joint.
- Dragging a slider rotates the corresponding link in RViz.

:::tip["What is xacro doing?"]
The `.xacro` file is a Jinja-ish macro language for URDFs. The top-level
`lite.urdf.xacro` includes `lite.ros2_control.xacro`, which selects the
`<plugin>` based on the `use_sim` / `use_fake_hardware` args. For RViz
visualization we force `use_fake_hardware:=true` so the `<ros2_control>`
block is harmless (`mock_components/GenericSystem`, which never gets
loaded because RViz doesn't spawn `controller_manager`).
:::

Close the launch (`Ctrl+C` in the terminal) before moving on.

## Step 2 — Bring up MuJoCo

Now the full control plane against MuJoCo physics: `controller_manager`
hosted inside `mujoco_sim`, all five mode-FSM controllers loaded, the
`mode_manager` orchestrator running. Nothing on the CAN bus — the
`MujocoSystem` hardware plugin applies the same MIT-mode torque
`τ = K·(q_cmd − q) + D·(q̇_cmd − q̇) + effort` to `qfrc_applied` that
the Robstride firmware computes on silicon.

```sh
ros2 launch bar_bringup_lite mujoco.launch.py
```

A **MuJoCo viewer window** opens with the Lite humanoid at zero pose.
The single `mujoco_sim` process hosts MuJoCo physics, the
`MujocoRos2ControlPlugin` (loaded as a pluginlib physics plugin), the
`controller_manager` inside that, and the `MujocoSystem` hardware
interface inside that. From the controller's point of view nothing
distinguishes this from real hardware — same 5 command interfaces, same
3 state interfaces.

![flowchart LR](/img/diagrams/quick_start__lite_101__04.svg)

Wait ~2 seconds, then in a **second terminal**:

```sh
source ~/bar_ws/install/setup.bash
ros2 control list_controllers
```

Expected output (give or take):

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

`zero_torque_controller` is active as the **safe startup default**: it
claims all 5 command interfaces on every joint and writes 0 to all of
them every tick. From an operator's perspective the robot is "alive but
inert".

The four other controllers are **loaded but inactive**. Loading them
runs their `on_configure` (params parsed, publishers/subscribers created)
without claiming the command interfaces. They sit ready to be activated
in a single service call.

### Watch the topics

```sh
ros2 topic list | grep -E "joint_states|control_mode|standby|safety"
# /control_mode
# /joint_states
# /safety_status
# /standby_controller/state
```

`joint_state_broadcaster` publishes `/joint_states` at the
controller_manager's update rate (50 Hz):

```sh
ros2 topic hz /joint_states
# average rate: 50.000
```

`mode_manager` publishes `/control_mode` (the current FSM state) at the
same rate:

```sh
ros2 topic echo --once /control_mode
# mode: 0           # ZERO_TORQUE
# controller_name: zero_torque_controller
# status_message: ''
```

:::tip["See it move"]
Two optional live visualizers ride on top of `/joint_states` +
`/robot_description` — add either flag to the launch you just ran:

```sh
# Native rerun viewer:
ros2 launch bar_bringup_lite mujoco.launch.py enable_rerun_viz:=true

# Browser viewer at http://localhost:8080 (good for headless machines):
ros2 launch bar_bringup_lite mujoco.launch.py enable_viser_viz:=true
```

Both can run simultaneously. Pip install once: `pip install rerun-sdk`
and/or `pip install viser yourdfpy 'scipy>=1.13'`. A dedicated *How-to →
Live visualization* page is coming.
:::

## Step 3 — Trigger a mode transition

The whole project is built around mode transitions: the operator (or a
fault) requests an *intent*, `mode_manager` resolves it to a controller
switch, and the controller_manager swaps the active controller. For
this lesson we'll just call the controller_manager service directly to
simulate what `mode_manager` would have done in response to the gamepad
`X` (DAMP) intent.

```sh
ros2 control switch_controllers \
    --activate damping_controller \
    --deactivate zero_torque_controller
```

Verify:

```sh
ros2 control list_controllers
# damping_controller        bar/DampingController                           active
# zero_torque_controller    bar/ZeroTorqueController                        inactive
```

:::tip[Why DAMPING is the "compliant fail-safe"]
With stiffness `K = 0` there's no position-restoring force. With damping
`D` nonzero the joint resists velocity. The result: the robot is **soft
under gravity** (push the arm and it moves) but **damped** (it doesn't
oscillate). This is the state you transition into before powering down,
before swapping a tool, or after any non-OK `SafetyStatus`. A
*Concepts → Five-mode FSM* page is coming; meanwhile see
[`bar_controllers` → DampingController](../reference/controllers.md#bardampingcontroller).
:::

If gravity is on (it is by default in our MJCF) and you switched to
DAMPING after a few seconds in ZERO_TORQUE, the arms in the MuJoCo
viewer should now **sag and settle** rather than freely flopping — the
damping resists fall velocity but the zero stiffness can't hold them
up. That contrast between the two modes is the lesson of this step.

## Step 4 — Switch back, then exit

Always end a session in a known safe state. Switch back to ZERO_TORQUE,
which makes the motors fully compliant again:

```sh
ros2 control switch_controllers \
    --activate zero_torque_controller \
    --deactivate damping_controller
```

Then `Ctrl+C` the launch terminal. The plugin's `on_deactivate` runs,
sending Disable to every joint (no-op in MuJoCo but matters on silicon),
and `mujoco_sim` shuts down cleanly.

## What you just saw

Four moving pieces, all worth recognising for the rest of the docs:

| Piece | What it does |
|---|---|
| **URDF** (`bar_description_lite`) | Kinematic + dynamic description. Same file across mock / sim / real — the `<ros2_control>` `<plugin>` is the only difference. |
| **`controller_manager`** | Hosts the hardware plugin + every controller. The "tick loop" of the system. Update rate 50 Hz here. |
| **Mode-FSM controllers** (`bar_controllers`) | Five plugins, one active at a time. `zero_torque` (safe default), `damping` (compliant fail-safe), `standby` (interpolate to a pose), `rl_policy` (in-process ONNX), `remote_policy` (out-of-process Python). |
| **MuJoCo / Robstride** (the simulation / real backend) | Where the MIT torque actually gets applied. Same five command interfaces in both. |

## Next

Where to go from here, depending on what you want:

- **I want to understand the design rationale.**
  → [Concepts → Architecture](../concepts/architecture.md).
- **I want the per-controller parameter reference.**
  → [Reference → Controllers](../reference/controllers.md).
- **I want the launch-arg reference.**
  → [Reference → Launch args](../reference/launch_args.md).
- **I want the per-package overview.**
  → [Reference → Packages](../reference/packages.md).

Three further pages are being written and will land here as they're ready:
*How-to → First real-hardware bringup*, *Tutorials → MuJoCo + FSM walkthrough*,
*Reference → Quick reference card*.
