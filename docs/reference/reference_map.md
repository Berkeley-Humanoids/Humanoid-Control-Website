# Reference map

A survey of the open robot low-level control ecosystem we studied while
designing `humanoid_control`. It is **descriptive**, not prescriptive: each entry
records *what the reference is* and *the role it played in our study*, so a
contributor can go read the primary source. Where `humanoid_control` made a
specific design choice, the rationale lives in the
[Concepts](../concepts/index.md) pages — this page is the map, not the
decision log.

The recurring lesson across all of these is the same **layered split**:
application/task → policy/controller → middleware/integration → hardware
abstraction → transport/bus → actuator firmware. The names differ; the
layering is remarkably consistent (see [Common layering](#common-layering-pattern)).

## Golden references — ROS 2 & ros2_control

| Reference | Link | Role in the study |
|---|---|---|
| ROS 2 Jazzy — About ROS | [https://docs.ros.org/en/jazzy/About-ROS.html](https://docs.ros.org/en/jazzy/About-ROS.html) | Baseline vocabulary: nodes, interfaces, parameters, client libraries, tooling. |
| ROS 2 — Interfaces (msg/srv/action) | [https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html](https://docs.ros.org/en/jazzy/Concepts/Basic/About-Interfaces.html) | High-rate state/command → topics; controller management → services; long goals → actions. |
| ROS 2 — Quality of Service | [https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Quality-of-Service-Settings.html) | History/depth/reliability/durability/deadline/liveliness — why control vs. logging traffic want different profiles. |
| ROS 2 — Executors | [https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-Executors.html) | Callback scheduling and its interaction with control-loop timing and data freshness. |
| ROS 2 — Real-time programming demo | [https://docs.ros.org/en/jazzy/Tutorials/Demos/Real-Time-Programming.html](https://docs.ros.org/en/jazzy/Tutorials/Demos/Real-Time-Programming.html) | The "what not to do in the RT path" list: page faults, dynamic allocation, blocking sync; `mlockall`, latency measurement. |
| ros2_control — Getting started | [https://control.ros.org/jazzy/doc/getting_started/getting_started.html](https://control.ros.org/jazzy/doc/getting_started/getting_started.html) | The core architecture `humanoid_control` is built on: controller manager, resource manager, controllers, hardware components. |
| ROS 2 code style | [https://docs.ros.org/en/rolling/The-ROS2-Project/Contributing/Code-Style-Language-Versions.html](https://docs.ros.org/en/rolling/The-ROS2-Project/Contributing/Code-Style-Language-Versions.html) · [REP-8](https://ros.org/reps/rep-0008.html) | The style floor for our C++ / Python packages. |

### ros2_control in one paragraph

The **controller manager** owns the real-time loop; each tick it reads
hardware state, runs every active controller's `update()`, and writes
commands back. The **resource manager** abstracts physical hardware as
pluginlib-loaded *hardware components* exposing **state** and **command**
interfaces. Controllers derive from `controller_interface::ControllerInterface`
and follow the ROS 2 lifecycle. Hardware components come in three kinds —
`System` (complex multi-DOF), `Sensor` (read-only), `Actuator` (1-DOF).
This is exactly the spine described in
[Architecture](../concepts/architecture.md).

## Control frameworks

| Reference | Link | What we took from it |
|---|---|---|
| legged_control2 | [https://qiayuanl.github.io/legged_control2_doc/overview.html](https://qiayuanl.github.io/legged_control2_doc/overview.html) | C++ toolbox for legged robots on `pinocchio` + `ros2_control`; RL-policy deployment, MuJoCo/Gazebo sim-to-sim, and a **unified hardware-interface** split (bus library vs. per-robot plugin) we mirror on the CAN side. |
| rm_control | [https://github.com/rm-controls/rm_control/](https://github.com/rm-controls/rm_control/) | A mature ros2_control-style codebase whose **package decomposition** (`*_common` / `*_hw` / `*_msgs` / sim / referee) is a template for splitting hardware, sim, comms, and control while staying in one repo; also its in-repo `industrial_ci`. |
| libfranka | [https://github.com/frankarobotics/libfranka](https://github.com/frankarobotics/libfranka) | A vendor-supported **real-time hardware client library** outside the ros2_control abstraction — useful contrast: joint position / impedance / torque control loops, real-time kernel + network setup. |
| whole_body_tracking / BeyondMimic | [https://github.com/HybridRobotics/whole_body_tracking](https://github.com/HybridRobotics/whole_body_tracking) | The **training side** of humanoid whole-body motion tracking on Isaac Lab; deployment is a separate motion-tracking controller — the same training/deployment split we use. |
| cyclo_control | [https://github.com/ROBOTIS-GIT/cyclo_control](https://github.com/ROBOTIS-GIT/cyclo_control) | ros2_control + `pinocchio` + OSQP for QP-based Cartesian/joint control and teleop retargeting on ROS 2 Jazzy. |

## Hardware, actuators & SDKs

| Reference | Link | Role |
|---|---|---|
| OpenArm software / ROS 2 control | [https://docs.openarm.dev/software/ros2/control/](https://docs.openarm.dev/software/ros2/control/) | A concrete ros2_control integration over **SocketCAN** with mock + real hardware, bringup launch/config parameters, and explicit hardware-safety guidance. |
| Unitree SDK2 Python | [https://github.com/unitreerobotics/unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python) | The canonical **no-`rclpy`, talk-DDS-directly** pattern (CycloneDDS) — the model for our [Tier-3](../concepts/workspace_and_environment.md) processes. Low-level joint/IMU/battery read + torque control; high-level must be disabled first. |
| RobStride actuator bridge | [https://github.com/MuShibo/robstride_actuator_bridge](https://github.com/MuShibo/robstride_actuator_bridge) | A compact CAN/ROS bridge and CAN-bringup flow (`slcan`, `1 Mbit/s`) — framing reference for our Robstride driver. |
| eRob ROS2 MoveIt | [https://github.com/ZeroErrControl/eRob_ROS2_MoveIt](https://github.com/ZeroErrControl/eRob_ROS2_MoveIt) | A working `ethercat_driver_ros2` + eRob integration — the primary template for the Prime **EtherCAT** bringup (IgH master, PDO mapping). |
| eRob SOEM Linux | [https://github.com/ZeroErrControl/eRob_SOEM_linux](https://github.com/ZeroErrControl/eRob_SOEM_linux) | SOEM examples (CSP/PP/CSV/PT) and the EtherCAT operational-state / DC-clock / object-dictionary / CPU-isolation concerns — reference if a custom plugin is ever needed. |
| Agibot X1 developer guide | [https://www.agibot.com.cn/DOCS/OS/X1-PDG](https://www.agibot.com.cn/DOCS/OS/X1-PDG) | Open humanoid hardware/software flow; **actuator confirmation & setup** (CAN-ID, firmware, MIT hybrid mode, user zero offset) as a bring-up checklist. |

## RL / sim-to-real deployment

| Reference | Link | Role |
|---|---|---|
| holosoma inference | [https://github.com/amazon-far/holosoma/tree/main/src/holosoma_inference](https://github.com/amazon-far/holosoma/tree/main/src/holosoma_inference) | Policy inference/deployment for humanoid locomotion + whole-body tracking across Unitree G1 / Booster / sim; **state-preprocessing-in-the-runtime** pattern. |
| instinct_onboard | [https://github.com/project-instinct/instinct_onboard](https://github.com/project-instinct/instinct_onboard) | Onboard inference (Unitree G1, Jetson Orin NX) with **ONNX Runtime CPU/GPU auto-dispatch** and MCAP logging — reference for our in-process ONNX path. |
| legged_control template controller | [https://github.com/qiayuanl/legged_template_controller](https://github.com/qiayuanl/legged_template_controller) | Minimal legged-RL controller skeleton. |

These map onto `humanoid_control` as: the **training side** (BeyondMimic,
`pianist-tracking-mj`) produces a self-describing ONNX; the **deployment
side** runs it in-process in `RLPolicyController` (see
[Tracking policy](../tutorials/tracking_policy.md) and
[Policy runner](./policy_runner.md)).

## Transport & bus references

- **DDS** — ROS 2 core comms and Unitree SDK2 both ride CycloneDDS.
  Concerns: QoS selection, message compatibility, NIC binding, discovery,
  lossy-network behaviour. This is the wire `humanoid_control_msgs_dds` targets.
- **CAN / SocketCAN** — OpenArm and the RobStride bridge:
  `can0`/`slcan` → CAN frames → motor protocol → actuator. The basis for
  `humanoid_drivers_socketcan` + `humanoid_devices_robstride` / `humanoid_devices_sito`.
- **EtherCAT** — eRob SOEM/IGH and `legged_control2`'s SOEM interfaces:
  SOEM or IgH master, Distributed Clock, object-dictionary mapping,
  OP-state transitions, real-time kernel + CPU isolation. The basis for
  the Prime path via `ethercat_driver_ros2`.

## Common layering pattern

Every reference above separates robot software into the same conceptual
stack, even when the names differ:

```text
Application / task     teleop · locomotion command · trajectory · motion tracking · manipulation
Policy / controller    PID · impedance · trajectory · whole-body · RL policy · inference runtime
Middleware             ROS 2 nodes · controller_manager · topics/services/actions · QoS · launch
Hardware abstraction   ros2_control hardware component · vendor SDK wrapper · CAN/EtherCAT driver
Transport / bus        DDS · SocketCAN · CANopen-like protocol · EtherCAT (SOEM/IgH) · USB-CAN
Actuator / embedded    motor firmware · drive state machine · encoder/current loop · safety · calibration
```

`humanoid_control` lands its own packages on this stack as described in
[Architecture](../concepts/architecture.md) and the
[Packages reference](./packages.md).

## Quick cross-reference by topic

| Topic | Primary references |
|---|---|
| ROS 2 conceptual model | About ROS · Interfaces · QoS · Executors |
| ROS-native control abstraction | ros2_control Getting Started |
| Real-time loop concerns | ROS 2 RT demo · libfranka · eRob SOEM |
| Hardware component abstraction | ros2_control · OpenArm · legged_control2 |
| Legged-robot RL deployment | legged_control2 · holosoma · instinct_onboard · BeyondMimic |
| Whole-body tracking (training) | whole_body_tracking / BeyondMimic |
| Unitree SDK / DDS | Unitree SDK2 Python |
| CAN actuator bring-up | OpenArm · RobStride bridge · Agibot X1 |
| EtherCAT / SOEM | eRob SOEM · eRob ROS2 MoveIt · legged_control2 |
| Vendor direct real-time API | libfranka |
