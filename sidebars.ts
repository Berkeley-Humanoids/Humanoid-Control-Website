import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// Five-section Diátaxis-derived layout
// (https://diataxis.fr/). The progression mirrors Isaac Lab / Nav2 /
// MoveIt 2: arrive → install → first lesson → more lessons → tasks →
// understand → look up.
//
// - Getting started : intro + install + the one canonical tutorial.
// - Tutorials       : learning-oriented. Build skill, no production realism.
// - How-to guides   : task-oriented recipes. Assume baseline familiarity.
// - Concepts        : understanding-oriented. The "why" layer.
// - Reference       : information-oriented. Dense, scannable, complete.
//
// Items are added to each category as the pages are written. Keep this file
// in sync with docs/ — Docusaurus fails the build on missing doc ids.
const sidebars: SidebarsConfig = {
  docs: [
    {
      type: 'category',
      label: 'Getting started',
      collapsed: false,
      items: [
        'getting_started/intro',
        'getting_started/installation',
        'getting_started/lite_101',
      ],
    },
    {
      type: 'category',
      label: 'Tutorials',
      collapsed: true,
      items: [
        'tutorials/index',
      ],
    },
    {
      type: 'category',
      label: 'How-to guides',
      collapsed: true,
      items: [
        'how_to/index',
      ],
    },
    {
      type: 'category',
      label: 'Concepts',
      collapsed: true,
      items: [
        'concepts/index',
        'concepts/architecture',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      collapsed: true,
      items: [
        'reference/quick_reference',
        'reference/hardware_specs',
        'reference/packages',
        'reference/messages',
        'reference/controllers',
        'reference/launch_args',
        'reference/policy_runner',
        // remaining pages (manual_controllers, topics_services, cli_tools,
        // urdf_args, troubleshooting) will land in Batch 4.
      ],
    },
  ],
};

export default sidebars;
