// The primary SVG owns the geometry. Regenerate derivatives with:
// node scripts/generate-brand.mjs (from web/). No build step or dependency needed.
import { readFile, writeFile } from "node:fs/promises";

const primary = await readFile(new URL("../public/brand/crewflow-icon.svg", import.meta.url), "utf8");
const monochrome = primary
  .replace(/      <rect[^\n]+\n/, "")
  .replace('stroke="#FFFFFF"', 'stroke="currentColor"');

await writeFile(new URL("../public/brand/crewflow-monochrome.svg", import.meta.url), monochrome);
// Favicons must be self-contained: external SVG <use> resources are unreliable here.
await writeFile(new URL("../public/favicon.svg", import.meta.url), primary);
