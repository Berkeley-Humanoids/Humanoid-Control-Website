import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// https://docusaurus.io/docs/api/docusaurus-config
const config: Config = {
  title: 'bar_ros2',
  tagline: 'BAR humanoid low-level control stack',
  favicon: 'img/logo.svg',

  // Production URL. Change to your real domain (or '/bar_ros2_docs/' if
  // serving under a GitHub Pages sub-path).
  url: 'https://bar-ros2-docs.example.invalid',
  baseUrl: '/',

  // GitHub Pages deploy config (only used by `docusaurus deploy`).
  organizationName: 'T-K-233',
  projectName: 'bar_ros2_docs',

  // Fail the build on broken internal links — same policy as VitePress.
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'throw',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl:
            'https://github.com/T-K-233/bar_ros2_docs/tree/main/',
          routeBasePath: '/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/logo.svg',
    colorMode: {
      defaultMode: 'light',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'bar_ros2',
      logo: {
        alt: 'BAR humanoid logo',
        src: 'img/logo.svg',
      },
      items: [
        {
          to: '/overview/intro',
          label: 'Overview',
          position: 'left',
        },
        {
          to: '/quick_start/installation',
          label: 'Quick start',
          position: 'left',
        },
        {
          to: '/reference/packages',
          label: 'Reference',
          position: 'left',
        },
        {
          href: 'https://github.com/T-K-233/bar_ros2',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Introduction', to: '/overview/intro'},
            {label: 'Hardware specs', to: '/overview/hardware_specifications'},
            {label: 'Software framework', to: '/overview/software_framework'},
          ],
        },
        {
          title: 'Quick start',
          items: [
            {label: 'Installation', to: '/quick_start/installation'},
            {label: 'bar_ros2 101', to: '/quick_start/lite_101'},
          ],
        },
        {
          title: 'Project',
          items: [
            {
              label: 'bar_ros2 on GitHub',
              href: 'https://github.com/T-K-233/bar_ros2',
            },
            {
              label: 'Berkeley Architecture Research',
              href: 'https://github.com/Berkeley-Humanoids',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} BAR Dev. Built with Docusaurus. BSD-3-Clause.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'yaml', 'cmake', 'cpp', 'python', 'xml-doc', 'json'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
