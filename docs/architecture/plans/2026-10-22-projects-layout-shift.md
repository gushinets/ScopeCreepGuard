# Projects onboarding layout shift

Issue: reported layout shift on Projects. Base/branch: existing
`codex/design-onboarding` from origin/main f3e34de. Preserve the uncommitted
redesign/onboarding work; no checkout, reset, push or PR.

Browser reproduction: on a new user's Projects page the coachmark changes from
inline to floating after initial layout, moving the collection by 131.7px.
ResizeObserver measurement can promote an already displayed inline fallback into
a portal after fonts/target dimensions settle.
The collision check also treated a short heading's full block width as occupied,
making placement depend on the space inserted by the tooltip itself. Measure
actual text rectangles while protecting complete control hit areas and table data.

Scope: stabilize automatic coachmark placement after it has chosen inline
fallback. A deliberate viewport resize may choose again. Preserve collision
avoidance, mobile placement, Skip, keyboard focus and database state behavior.
No project or pricing logic changes.

Steps: fix placement lifecycle; add a regression for late target remeasurement;
run Docker tests/build/lint; measure Projects geometry in a browser across desktop
and phone widths, including resize and EN/RU. Record results here.

Owner: current chat. Limits: ordinary asynchronous workspace loading is separate
from the reproduced inline/portal movement. No deployment or push is requested.

## Result

Collision checks now use rendered text rectangles, including table metadata, and
full hit areas for controls. An inline fallback remains inline during passive
remeasurement; an explicit viewport resize can choose a new safe position. The
inline breakpoint now matches the shell's <=1100px breakpoint.

Browser before/after: the English empty collection at 1440px previously alternated
between y=316.7 and y=185. After the fix it stays at y=185 with the guide floating
beside New project. The 1280px layout also stays at y=185. Sampling 75 consecutive
frames at each of 1440/1280/1100/768/390px found one stable content position per
viewport. Russian live resizing through those widths and back to 1440px also
stayed stable after each resize, with no horizontal overflow. Skip still persists.
This is not a claim of zero CLS for the initial asynchronous workspace load.

Docker: 19 onboarding/project UI tests passed, including regressions for late
remeasurement and full-width text-block whitespace. TypeScript/production build,
frontend lint and dependency boundaries (94 modules), and Git whitespace checks
passed. The pre-existing bundle-size warning remains. No backend changes.

Screenshots:
[Desktop](../evidence/2026-10-22-design-onboarding/screenshots/projects-shift-fixed-desktop.png),
[phone](../evidence/2026-10-22-design-onboarding/screenshots/projects-shift-fixed-mobile.png).
All earlier work remains uncommitted on codex/design-onboarding; no push or PR.
