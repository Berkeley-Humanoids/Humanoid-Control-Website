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
        'tutorials/drive_one_robstride',
        'tutorials/mujoco_fsm_walk',
        'tutorials/tracking_policy',
        'tutorials/build_your_own_controller',
      ],
    },
    {
      type: 'category',
      label: 'How-to guides',
      collapsed: true,
      items: [
        'how_to/index',
        'how_to/first_real_bringup',
        'how_to/calibrate_zero_pose',
        'how_to/probe_can_bus',
        'how_to/switch_controllers_manually',
        'how_to/mit_slider_gui',
        'how_to/live_viz',
        'how_to/diagnose_enobufs',
        'how_to/recover_from_fault',
        'how_to/promote_python_to_cpp',
        'how_to/add_new_joint',
      ],
    },
    {
      type: 'category',
      label: 'Concepts',
      collapsed: true,
      items: [
        'concepts/index',
        'concepts/architecture',
        'concepts/five_mode_fsm',
        'concepts/mit_command_surface',
        'concepts/calibration_math',
        'concepts/safety_pipeline',
        'concepts/frozen_schemas',
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
        'reference/manual_controllers',
        'reference/launch_args',
        'reference/policy_runner',
        'reference/topics_services',
        'reference/cli_tools',
        'reference/urdf_args',
        'reference/troubleshooting',
      ],
    },
  ],
};

export default sidebars;
