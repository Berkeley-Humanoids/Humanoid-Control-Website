# Humanoid-Control-Website

Documentation site for [`humanoid_control`](https://github.com/Berkeley-Humanoids/humanoid_control) — the
Berkeley Architecture Research (BAR) humanoid low-level control stack.

Built with [Docusaurus 3](https://docusaurus.io/) + `@docusaurus/theme-mermaid`
for source-controlled diagrams of the control flow, FSM, and package
architecture.

## Develop

```sh
npm install
npm start            # http://localhost:3000, hot reload
```

## Build

```sh
npm run build        # output: build/
npm run serve        # serve the built dist locally
```

## Deploy

The `build/` directory is a fully static site — drop it on Netlify,
Cloudflare Pages, or GitHub Pages. For GitHub Pages, configure the workflow
to publish `build/`; the bundled `docusaurus.config.ts` already sets
`organizationName` and `projectName` for a `Berkeley-Humanoids/Humanoid-Control-Website` repo.

## Layout

```
.
├── docusaurus.config.ts          (nav, footer, mermaid, deploy config)
├── sidebars.ts                   (single sidebar, three categories)
├── tsconfig.json                 (extends @docusaurus/tsconfig)
├── src/
│   ├── pages/index.tsx           (React homepage)
│   ├── components/HomepageFeatures/   (feature cards on the homepage)
│   └── css/custom.css            (Berkeley blue + gold palette)
├── static/img/                   (logo, favicon, social card)
└── docs/
    ├── overview/
    │   ├── intro.md
    │   ├── hardware_specifications.md
    │   └── software_framework.md
    ├── quick_start/
    │   ├── installation.md
    │   └── lite_101.md
    └── reference/
        ├── packages.md
        ├── messages.md
        ├── controllers.md
        └── launch_args.md
```

## Authoring conventions

- **Diagrams**: prefer Mermaid in fenced code blocks (\`\`\`mermaid). Avoid binary
  images for anything expressible as a graph, sequence, or state diagram —
  they version-control cleanly.
- **Admonitions (Docusaurus 3 syntax)**: `:::tip[Optional title]` (title in
  brackets attached to the fence — not space-separated).
- **Cross-links**: use relative paths. Docusaurus strips the `.md`
  extension at build time.
