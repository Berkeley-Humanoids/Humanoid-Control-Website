import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import HomepageFeatures from '@site/src/components/HomepageFeatures';

import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <p className={styles.tagDetail}>
          A unified <code>ros2_control</code> stack for the Berkeley Architecture
          Research bimanual humanoids — same controllers, same MIT-mode interfaces,
          mock / MuJoCo / real CAN selectable from a single xacro arg.
        </p>
        <div className={styles.buttons}>
          <Link
            className="button button--primary button--lg"
            to="/getting_started/lite_101">
            Quick start →
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/getting_started/intro">
            What is this?
          </Link>
          <Link
            className="button button--secondary button--lg"
            to="/reference/packages">
            Reference
          </Link>
          <Link
            className="button button--secondary button--lg"
            href="https://github.com/Berkeley-Humanoids/humanoid_control">
            GitHub
          </Link>
        </div>
      </div>
    </header>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={`${siteConfig.title} — ${siteConfig.tagline}`}
      description="Docs for humanoid_control, the humanoid_control humanoid low-level control stack.">
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
