# Introduction

`bar_ros2` is the unified low-level control stack for the **Berkeley Architecture
Research (BAR)** humanoid robots. It runs on **ROS 2 Jazzy / Ubuntu 24.04 under
PREEMPT_RT** and targets two robots with **as much shared code as possible**:

- **Lite** — a bimanual humanoid with **Robstride actuators on two SocketCAN
  buses** (CAN-to-USB), one bus per arm.
- **Prime** — a bimanual humanoid with **eRob actuators over EtherCAT** and
  **Sito actuators over SocketCAN**, running concurrently. The EtherCAT side is
  driven by the third-party
  [`ethercat_driver_ros2`](https://github.com/ICube-Robotics/ethercat_driver_ros2)
  (ICube Robotics), built on the IgH EtherLAB master.

> **The headline**: identical controllers, message schemas, simulation tooling,
> and bringup launches across both robots. Robot differences live entirely in
> URDF and hardware-component selection.

## What problem does this stack solve?

Humanoid control codebases historically split along a robot-by-robot,
hardware-by-hardware axis: separate plugins for each actuator family, separate
launch files per task, separate observation pipelines for sim vs. silicon. The
result is N × M code paths, where N is robots and M is tasks.

`bar_ros2` factors the axes orthogonally:

| Axis | Where the variation lives |
|---|---|
| Robot (Lite / Prime) | URDF + which `<ros2_control>` `<plugin>` is selected |
| Hardware tier (mock / sim / real) | a single xacro arg (`use_fake_hardware` / `use_sim`) |
| Task (locomotion / manipulation / VLA) | the active policy controller, swapped by `mode_manager` |
| Compute (in-process vs. out-of-process) | `RLPolicyController` (ONNX, C++) vs. `bar_policy` (Python) |

Everything else is shared.

## System at a glance

![flowchart TB](/img/diagrams/overview__intro__01.svg)

The two CAN buses on Lite are a **physical** split (one CAN-to-USB adapter per
arm), surfaced as **two `<ros2_control>` blocks** on the real-hardware path:
`LiteLeftArm` claims CAN ids 11..17 on `can_interface_left`, `LiteRightArm`
claims 21..27 on `can_interface_right`. The controller_manager runs both
plugin instances concurrently and exposes a single flat 14-joint list to
controllers — they don't see the split. Prime adds a third path through
`ethercat_driver_ros2` for the eRob side.

## How the project is organized

A single git repo at `T-K-233/bar_ros2`, a flat collection of ROS 2 packages
(franka_ros2 / Universal_Robots_ROS2_Driver pattern):

![flowchart LR](/img/diagrams/overview__intro__02.svg)

Notice that **`bar_controllers`, `bar_msgs`, and `bar_policy` have no
robot-specific code** — everything robot-specific lives in `bar_description_*`
or `bar_bringup_*`.

## Design rationale (one-paragraph version)

`ros2_control` is the integration spine. Every joint exposes **3 state
interfaces** (`position`, `velocity`, `effort`) and **5 command interfaces**
(`position`, `velocity`, `effort`, `stiffness`, `damping`) — the **MIT-mode
hybrid command** convention used by Cheetah, MIT Mini Cheetah, and the Berkeley
Humanoids deployments. The actuator (or sim, or mock) computes torque as

```
tau = K_p (q_cmd - q) + K_d (q_dot_cmd - q_dot) + tau_ff
```

This formula is identical in our Robstride firmware, in
`mujoco_ros2_control::MujocoSystem`, and in any controller we write — so the
same `update()` body works against silicon, MuJoCo, and `mock_components`. See
[Architecture](../concepts/architecture.md) for the full ros2_control flow.

## Reference materials

The architectural choices in this stack draw heavily on prior work. The
project's `AGENTS.md` (kept project-local, not in the git repo) cites the full
list; the most influential are:

- **[rm_control](https://github.com/rm-controls/rm_control)** — package
  decomposition pattern and `industrial_ci` workflow.
- **[legged_control2](https://qiayuanl.github.io/legged_control2_doc/overview.html)**
  — two-tier hardware factoring (bus library / per-actuator-family plugin)
  that we mirror for `bar_hw_socketcan` / `bar_hw_robstride` / `bar_hw_sito`.
- **[mujoco_ros2_control](https://github.com/qiayuanl/mujoco_ros2_control)** —
  the MuJoCo ↔ ros2_control bridge whose `MujocoSystem` plugin we consume.
- **[franka_ros2](https://github.com/frankarobotics/franka_ros2)** — the flat
  package-collection layout this repo follows.
- **[Universal_Robots_ROS2_Driver](https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver)**
  — gold-standard `ros2_control` hardware integration. The
  `Universal_Robots_Client_Library` / `ur_robot_driver` split mirrors our
  `bar_hw_socketcan` / `bar_hw_robstride` split.

## Next

- [Hardware specifications](../reference/hardware_specs.md) — joint counts,
  effort limits, transport details for Lite and Prime.
- [Architecture](../concepts/architecture.md) — ros2_control flow, the 5-mode
  FSM, the in-process vs. out-of-process policy tiers.
- [Installation](./installation.md) — install and run a Lite mock
  bringup in ~10 minutes.