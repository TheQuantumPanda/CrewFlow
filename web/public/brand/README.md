# CrewFlow brand assets

The original mark uses three coordinated paths: an outer C-shaped channel and
two inner paths joining its lower exit. It represents people taking ownership
of work and moving it through a shared system. No third-party artwork is used.

- `crewflow-icon.svg`: primary indigo tile and canonical SVG geometry. The
  `crewflow-mark` symbol can also be referenced with SVG `<use>`.
- `crewflow-monochrome.svg`: transparent, single-color geometry. Use its symbol
  inside an SVG with `color` set to a suitable foreground (navy on light,
  white on dark). Standalone images default to black.
- `../favicon.svg`: self-contained primary icon for browser compatibility.
- `src/components/Brand.tsx` (relative to `web/`): `CrewFlowBrand` is the reusable
  horizontal icon + live wordmark treatment. It uses the existing bundled
  Bricolage Grotesque font. `BrandMark` supports an optional accessible label;
  it is decorative by default when a nearby wordmark already names the app.

Edit only the canonical icon, then run from `web/`:

```sh
node scripts/generate-brand.mjs
```

The generator copies the primary geometry to the favicon and removes the tile
for the monochrome version. It requires only Node's standard library; no new
package or build configuration is needed. Palette changes in the canonical
SVG should also be reflected in the existing CSS tokens.
