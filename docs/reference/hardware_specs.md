# Hardware specifications

This page is the source of truth for **joint counts, actuator specs, and bus
topology** on Lite and Prime. The numbers here drive the joint limits in
`bar_description_*` and the per-joint stiffness/damping defaults in
`bar_controllers/config/bar_*_controllers.yaml`.

## Lite humanoid

Bimanual upper body. The design intent is **17 actuated DOFs** (7 per arm + 3
neck); the physical robot used for first bringup ships with **14 actuated
DOFs** (no neck). Re-add the third `<ros2_control>` block in
`lite.ros2_control.xacro` once the neck actuators are wired up — the URDF
kinematic chain for the neck is unchanged, so `robot_state_publisher` already
exposes the right tf.

![Lite kinematic tree](/img/diagrams/reference__hardware_specs__01.svg)

### Joint table

Order matches the **canonical index** used by `bar_lite_controllers.yaml`, the
C++ `MITState` struct, and the Python `bar_policy.ObservationManager`. Once a
policy is trained against this order, it is frozen — see "Frozen schemas" in
[Architecture](../concepts/architecture.md#frozen-schemas).

| Idx | Joint | CAN id | Bus | Model | Direction | Lower (rad) | Upper (rad) | Effort (Nm) | Current (A) | `K_p` | `K_d` |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | `left_shoulder_pitch`  | 11 | can0 | rs-02 | −1 | −3.142 | 0.785 | 17.0 | 27 | 50.0 | 2.0 |
| 1 | `left_shoulder_roll`   | 12 | can0 | rs-00 | −1 | −1.571 | 1.920 | 14.0 | 16 | 50.0 | 2.0 |
| 2 | `left_shoulder_yaw`    | 13 | can0 | rs-00 | +1 | −1.571 | 1.571 | 14.0 | 16 | 50.0 | 2.0 |
| 3 | `left_elbow_pitch`     | 14 | can0 | rs-00 | −1 | −2.356 | 0.000 | 14.0 | 16 | 50.0 | 2.0 |
| 4 | `left_wrist_yaw`       | 15 | can0 | rs-05 | +1 | −1.571 | 1.571 |  4.0 | 14 | 50.0 | 2.0 |
| 5 | `left_wrist_roll`      | 16 | can0 | rs-05 | −1 | −0.698 | 0.698 |  4.0 | 14 | 50.0 | 2.0 |
| 6 | `left_wrist_pitch`     | 17 | can0 | rs-05 | −1 | −0.785 | 0.785 |  4.0 | 14 | 50.0 | 2.0 |
| 7 | `right_shoulder_pitch` | 21 | can1 | rs-02 | +1 | −3.142 | 0.785 | 17.0 | 27 | 50.0 | 2.0 |
| 8 | `right_shoulder_roll`  | 22 | can1 | rs-00 | −1 | −1.920 | 1.571 | 14.0 | 16 | 50.0 | 2.0 |
| 9 | `right_shoulder_yaw`   | 23 | can1 | rs-00 | +1 | −1.571 | 1.571 | 14.0 | 16 | 50.0 | 2.0 |
| 10 | `right_elbow_pitch`   | 24 | can1 | rs-00 | +1 | −2.356 | 0.000 | 14.0 | 16 | 50.0 | 2.0 |
| 11 | `right_wrist_yaw`     | 25 | can1 | rs-05 | +1 | −1.571 | 1.571 |  4.0 | 14 | 50.0 | 2.0 |
| 12 | `right_wrist_roll`    | 26 | can1 | rs-05 | +1 | −0.698 | 0.698 |  4.0 | 14 | 50.0 | 2.0 |
| 13 | `right_wrist_pitch`   | 27 | can1 | rs-05 | −1 | −0.785 | 0.785 |  4.0 | 14 | 50.0 | 2.0 |

(Neck rows omitted — once the neck is wired, the canonical convention is
indices 14–16 = `neck_yaw`, `neck_roll`, `neck_pitch`, all rs-00-class with
`K_p ≈ 30`, `K_d ≈ 1`.)

:::tip[Where these numbers come from]
Limits / models / directions are mirrored from
[`T-K-233/Lite-Lowlevel-Python`](https://github.com/T-K-233/Lite-Lowlevel-Python)'s
`configs/bimanual.yaml`. They appear in the URDF as `<param>` children on each
`<joint>` and are consumed by `bar_hw_robstride/RobstrideSystem::on_init`.
Default stiffness / damping reflects a conservative MIT-mode setting suitable
for first activation; tune per deployment.
:::

### Transports

Lite uses **two SocketCAN buses** (CAN-to-USB adapters), one per arm. Each
bus is a separate `<ros2_control>` block in the URDF, each loading its own
`bar_hw_robstride/RobstrideSystem` instance:

| Block | Default ifname | CAN ids |
|---|---|---|
| `LiteLeftArm`  | `can_interface_left` (default `can0`) | 11..17 |
| `LiteRightArm` | `can_interface_right` (default `can1`) | 21..27 |

![Lite CAN topology](/img/diagrams/reference__hardware_specs__02.svg)

The controller_manager runs both plugin instances concurrently and exposes
a single flat 14-joint list to controllers — they don't see the split.

#### Bus-bring-up checklist

```sh
# 1. Bring up both buses at 1 Mbps.
sudo ip link set can0 down 2>/dev/null
sudo ip link set can0 up type can bitrate 1000000
sudo ip link set can1 down 2>/dev/null
sudo ip link set can1 up type can bitrate 1000000

# 2. Read-only sanity scan — no Enable, no MIT.
ros2 run bar_hw_robstride robstride_discover --iface can0 --scan-to 32
ros2 run bar_hw_robstride robstride_discover --iface can1 --scan-to 32
# Expect 7 + 7 = 14 actuators replying at ids 11..17 and 21..27.

# 3. Calibrate the zero pose (once per physical robot).
ros2 launch bar_bringup_lite calibrate.launch.py
# Hand-sweep every joint to both extremes. Ctrl+C to write calibration.json.

# 4. Real-hardware bringup.
ros2 launch bar_bringup_lite real.launch.py
```

If `robstride_discover` reports `ENOBUFS` / TX-drop warnings, the actuator
power is off (no ACKs → frames pile up in the kernel qdisc). Power the
motors first.

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

![MIT-mode hybrid command](/img/diagrams/reference__hardware_specs__03.svg)

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

- [Architecture](../concepts/architecture.md) — how this hardware surface is
  consumed by ros2_control and the mode FSM.
- [bar_lite_controllers.yaml](https://github.com/T-K-233/bar_ros2/blob/main/bar_controllers/config/bar_lite_controllers.yaml)
  — the canonical 17-joint binding for every controller.
- [`bar_hw_robstride/include/bar_hw_robstride/robstride_system.hpp`](https://github.com/T-K-233/bar_ros2/blob/main/bar_hw_robstride/include/bar_hw_robstride/robstride_system.hpp)
  — the SystemInterface implementation for the Lite hardware path.