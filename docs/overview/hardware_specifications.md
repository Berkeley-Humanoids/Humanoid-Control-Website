# Hardware specifications

This page is the source of truth for **joint counts, actuator specs, and bus
topology** on Lite and Prime. The numbers here drive the joint limits in
`bar_description_*` and the per-joint stiffness/damping defaults in
`bar_controllers/config/bar_*_controllers.yaml`.

## Lite humanoid

Bimanual upper body, **17 actuated DOFs**:

![graph TD](/img/diagrams/overview__hardware_specifications__01.svg)

### Joint table

Order matches the **canonical index** used by `bar_lite_controllers.yaml`, the
C++ `MITState` struct, and the Python `bar_policy.ObservationManager`. Once a
policy is trained against this order, it is frozen — see "Frozen schemas" in
[Software framework](software_framework.md#frozen-schemas).

| Idx | Joint | Lower (rad) | Upper (rad) | Effort (Nm) | Velocity (rad/s) | Default `K_p` | Default `K_d` |
|---|---|---:|---:|---:|---:|---:|---:|
| 0 | `left_shoulder_pitch`  | −3.142 | 0.785 | 17.0 | 100 | 50.0 | 2.0 |
| 1 | `left_shoulder_roll`   | −1.571 | 1.920 | 14.0 | 100 | 50.0 | 2.0 |
| 2 | `left_shoulder_yaw`    | −1.571 | 1.571 | 14.0 | 100 | 50.0 | 2.0 |
| 3 | `left_elbow_pitch`     | −2.356 | 0.000 | 14.0 | 100 | 50.0 | 2.0 |
| 4 | `left_wrist_yaw`       | −1.571 | 1.571 |  5.5 | 100 | 50.0 | 2.0 |
| 5 | `left_wrist_roll`      | −0.698 | 0.698 |  5.5 | 100 | 50.0 | 2.0 |
| 6 | `left_wrist_pitch`     | −0.785 | 0.785 |  5.5 | 100 | 50.0 | 2.0 |
| 7 | `right_shoulder_pitch` | −3.142 | 0.785 | 17.0 | 100 | 50.0 | 2.0 |
| 8 | `right_shoulder_roll`  | −1.920 | 1.571 | 14.0 | 100 | 50.0 | 2.0 |
| 9 | `right_shoulder_yaw`   | −1.571 | 1.571 | 14.0 | 100 | 50.0 | 2.0 |
| 10 | `right_elbow_pitch`   | −2.356 | 0.000 | 14.0 | 100 | 50.0 | 2.0 |
| 11 | `right_wrist_yaw`     | −1.571 | 1.571 |  5.5 | 100 | 50.0 | 2.0 |
| 12 | `right_wrist_roll`    | −0.698 | 0.698 |  5.5 | 100 | 50.0 | 2.0 |
| 13 | `right_wrist_pitch`   | −0.785 | 0.785 |  5.5 | 100 | 50.0 | 2.0 |
| 14 | `neck_yaw`            | −0.785 | 0.785 | 10.0 | 100 | 30.0 | 1.0 |
| 15 | `neck_roll`           | −0.524 | 0.524 | 10.0 | 100 | 30.0 | 1.0 |
| 16 | `neck_pitch`          | −0.524 | 0.524 | 10.0 | 100 | 30.0 | 1.0 |

:::tip[Where these numbers come from]
Limits are ported from the upstream
[`Berkeley-Humanoids/Robot-Descriptions/lite_dummy`](https://github.com/Berkeley-Humanoids/Robot-Descriptions/tree/main/robots/lite_dummy)
`joint_properties.json` (Robstride spec). Default stiffness / damping reflects
a conservative MIT-mode setting suitable for first activation; tune per
deployment.
:::

### Transports

Lite uses **two SocketCAN buses** (CAN-to-USB adapters), one per arm. The neck
shares a bus with one of the arms.

![flowchart LR](/img/diagrams/overview__hardware_specifications__02.svg)

:::warning[CAN id assignment is currently placeholder]
`bar_description_lite/urdf/lite.ros2_control.xacro` assigns sequential CAN ids
1..17 today. **Re-map these to your physical hardware** (DIP switches / vendor
tool) before any real-hardware bringup. Tracked in TODOS.md.
:::

### IMU

A single serial / USB IMU publishes `sensor_msgs/Imu` on `/imu/data`. It is
**not** routed through `ros2_control` as a `SensorInterface` — a blocking
serial read inside the controller_manager `read()` cycle would block the RT
loop. Consumers (RLPolicyController, bar_policy) cache the latest sample via
`realtime_tools::RealtimeBuffer`.

## Prime humanoid

Bimanual with EtherCAT-driven eRob actuators in the arms and SocketCAN-driven
Sito actuators for auxiliary joints, running concurrently in the same
`controller_manager`.

:::info[Prime URDF is not yet imported]
The Prime mechanical CAD has not been finalized at the time of writing.
`bar_description_prime` is a placeholder package; `bar_lite_controllers.yaml`
binds 17 real joints, but `bar_prime_controllers.yaml` is still
`["__placeholder__"]`. Joint specs below are projections, not commitments.
:::

### Projected joint topology

Prime is unique in that **two `<ros2_control>` blocks coexist** in its URDF —
one binds `ethercat_driver/EthercatDriver`, the other binds
`bar_hw_sito/SitoSystem`. The controller_manager runs both concurrently;
controllers see a single flat joint list regardless of which bus carries them.

## MIT-mode command convention

Every actuator on both robots (and every sim system) implements a **hybrid
position-velocity-torque command** that is the central abstraction of the
project:

![flowchart LR](/img/diagrams/overview__hardware_specifications__05.svg)

Every controller in `bar_controllers` claims **all five** command interfaces,
even when it only writes some of them (writing zero to the rest is the safe
default — for example `ZeroTorqueController` writes 0 to everything;
`DampingController` writes `K=0, D=damping_value, q_cmd=captured_q`).

:::tip[Why this convention pays off]
The exact same formula is implemented in the Robstride motor firmware, in
`mujoco_ros2_control::MujocoSystem` (verified in `mujoco_system.cpp`), and in
any controller we write. As a result a policy that ran on Lite in simulation
runs unchanged against the real Lite — no gain remapping, no quirk shims.
:::

The names `stiffness` and `damping` are taken **verbatim** from
`mujoco_ros2_control::MujocoSystem` (`HW_IF_STIFFNESS = "stiffness"`,
`HW_IF_DAMPING = "damping"`) so the same controller binds identically against
silicon and sim with no URDF interface-tag rewrites.

## Reference & next

- [Software framework](software_framework.md) — how this hardware surface is
  consumed by ros2_control and the mode FSM.
- [bar_lite_controllers.yaml](https://github.com/T-K-233/bar_ros2/blob/main/bar_controllers/config/bar_lite_controllers.yaml)
  — the canonical 17-joint binding for every controller.
- [`bar_hw_robstride/include/bar_hw_robstride/robstride_system.hpp`](https://github.com/T-K-233/bar_ros2/blob/main/bar_hw_robstride/include/bar_hw_robstride/robstride_system.hpp)
  — the SystemInterface implementation for the Lite hardware path.