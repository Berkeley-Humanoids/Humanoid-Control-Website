import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// Single sidebar with three categories. Docusaurus auto-collapses inactive
// categories on each page, mirroring the rm-control-docs sidebar shape.
const sidebars: SidebarsConfig = {
  docs: [
    {
      type: 'category',
      label: 'Overview',
      collapsed: false,
      items: [
        'overview/intro',
        'overview/hardware_specifications',
        'overview/software_framework',
      ],
    },
    {
      type: 'category',
      label: 'Quick start',
      collapsed: false,
      items: [
        'quick_start/installation',
        'quick_start/lite_101',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      collapsed: false,
      items: [
        'reference/packages',
        'reference/messages',
        'reference/controllers',
        'reference/policy_runner',
        'reference/launch_args',
      ],
    },
  ],
};

export default sidebars;
