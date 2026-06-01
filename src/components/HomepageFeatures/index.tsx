import type {ReactNode} from 'react';
import clsx from 'clsx';
import Heading from '@theme/Heading';
import styles from './styles.module.css';

type FeatureItem = {
  title: string;
  description: ReactNode;
};

const FeatureList: FeatureItem[] = [
  {
    title: 'Two robots, one codebase',
    description: (
      <>
        <strong>Lite</strong> (bimanual, Robstride on SocketCAN) and{' '}
        <strong>Prime</strong> (eRob over EtherCAT + Sito on SocketCAN) share
        every controller, policy, and message. Robot differences live entirely
        in URDF and hardware-plugin selection.
      </>
    ),
  },
  {
    title: 'Real-time-safe by construction',
    description: (
      <>
        C++20 on <code>ros2_control</code> + <code>realtime_tools</code>.{' '}
        <code>read()</code> / <code>update()</code> / <code>write()</code> are
        allocation-free; PREEMPT_RT scheduling and CPU pinning are first-class.
      </>
    ),
  },
  {
    title: 'MIT-mode hybrid commands',
    description: (
      <>
        Five command interfaces per joint (<code>position</code>,{' '}
        <code>velocity</code>, <code>effort</code>, <code>stiffness</code>,{' '}
        <code>damping</code>) — the same convention silicon, MuJoCo, and mock
        hardware all honor, so policies port across tiers without re-mapping.
      </>
    ),
  },
  {
    title: 'Five-mode FSM',
    description: (
      <>
        <code>ZERO_TORQUE</code> → <code>DAMPING</code> → <code>STANDBY</code> →{' '}
        <code>LOCOMOTION</code> | <code>REMOTE</code>. The gamepad picks the
        policy at the button — there's no launch-time arg. Safety status
        auto-falls to <code>DAMPING</code>; every transition is one{' '}
        <code>switch_controller</code> call.
      </>
    ),
  },
  {
    title: 'MuJoCo sim2real',
    description: (
      <>
        MuJoCo applies the same MIT-mode torque formula via{' '}
        <code>qfrc_applied</code> that our Robstride firmware computes —
        controllers and trained policies run unchanged against silicon and sim.
      </>
    ),
  },
  {
    title: 'Out-of-process VLA tier',
    description: (
      <>
        Heavy transformer / diffusion policies live in a Python <code>rclpy</code>{' '}
        node and publish <code>MITAction</code> over DDS.{' '}
        <code>ObservationManager</code> mirrors the C++ side structurally so
        policies promote between tiers without index drift.
      </>
    ),
  },
];

function Feature({title, description, index}: FeatureItem & {index: number}) {
  return (
    <div className={clsx('col col--4')}>
      <div className={styles.featureCard}>
        <div className={styles.featureBadge} aria-hidden="true">
          {String(index + 1).padStart(2, '0')}
        </div>
        <Heading as="h3" className={styles.featureTitle}>{title}</Heading>
        <p className={styles.featureDescription}>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): ReactNode {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} index={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
