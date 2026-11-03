# Vendored shadcn stylesheet

`shadcn.css` is an unmodified copy of `dist/tailwind.css` from the npm package
`shadcn@4.10.0`, previously resolved by this application's pnpm lockfile.

- Package: https://registry.npmjs.org/shadcn/-/shadcn-4.10.0.tgz
- Source: https://github.com/shadcn-ui/ui/tree/shadcn%404.10.0/packages/shadcn
- License: MIT, copyright (c) 2023 shadcn; full notice in `shadcn.LICENSE`.
- The same notice is shipped in production at `/licenses/shadcn.txt`.
- License source: https://raw.githubusercontent.com/shadcn-ui/ui/shadcn%404.10.0/LICENSE.md
- SHA-256 of the original and vendored CSS: `146941ac3ff65496fdf1cb306e697255328e4dadc7c105d66e36bb031b00f6d6`.

The complete stylesheet is retained, including accordion keyframes, custom data
variants and the scrollbar utility. It has no external imports or asset references.
`globals.css` imports it after Tailwind and tw-animate-css, in the original order.
The CLI is unnecessary for building or running the application. `components.json`
remains useful as optional component-generation configuration.

For future updates, compare the corresponding upstream release stylesheet and
license, replace the complete file, update this provenance and verify compiled CSS
and representative component states. Installing the CLI is not required.
