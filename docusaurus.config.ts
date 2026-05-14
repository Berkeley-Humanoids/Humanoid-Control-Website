import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

// https://docusaurus.io/docs/api/docusaurus-config
const config: Config = {
  title: 'bar_ros2',
  tagline: 'BAR humanoid low-level control stack',
  favicon: 'img/logo.svg',

  // Production URL for GitHub Pages project site.
  url: 'https://t-k-233.github.io',
  baseUrl: '/BAR-ROS2-Docs/',

  organizationName: 'T-K-233',
  projectName: 'BAR-ROS2-Docs',
  trailingSlash: false,

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
        {to: '/getting_started/intro', label: 'Getting started', position: 'left'},
        {to: '/tutorials/',            label: 'Tutorials',       position: 'left'},
        {to: '/how_to/',               label: 'How-to',          position: 'left'},
        {to: '/concepts/',             label: 'Concepts',        position: 'left'},
        {to: '/reference/packages',    label: 'Reference',       position: 'left'},
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
          title: 'Getting started',
          items: [
            {label: 'Introduction',  to: '/getting_started/intro'},
            {label: 'Installation',  to: '/getting_started/installation'},
            {label: 'Lite 101',      to: '/getting_started/lite_101'},
          ],
        },
        {
          title: 'Learn',
          items: [
            {label: 'Tutorials',     to: '/tutorials/'},
            {label: 'How-to guides', to: '/how_to/'},
            {label: 'Concepts',      to: '/concepts/'},
          ],
        },
        {
          title: 'Reference',
          items: [
            {label: 'Hardware specs',  to: '/reference/hardware_specs'},
            {label: 'Packages',        to: '/reference/packages'},
            {label: 'Controllers',     to: '/reference/controllers'},
            {label: 'Launch args',     to: '/reference/launch_args'},
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
