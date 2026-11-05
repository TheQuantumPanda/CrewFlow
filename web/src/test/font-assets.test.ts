// @vitest-environment node
import { copyFileSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { build, mergeConfig } from "vite";
import { expect, it } from "vitest";

import config from "../../vite.config";

it("emits the actual small font subsets for self-only CSP while retaining small SVG inlining", async () => {
  const root = mkdtempSync(join(tmpdir(), "crewflow-font-regression-"));
  const originals = new Map<string, Buffer>();
  try {
    for (const family of ["manrope", "jetbrains-mono"]) {
      const source = fileURLToPath(new URL(`../../node_modules/@fontsource-variable/${family}/files/${family}-cyrillic-ext-wght-normal.woff2`, import.meta.url));
      originals.set(family, readFileSync(source));
      copyFileSync(source, join(root, `${family}.woff2`));
    }
    writeFileSync(join(root, "index.html"), '<html><head><link rel="stylesheet" href="/fixture.css"></head><body>Font build fixture</body></html>');
    writeFileSync(join(root, "small.svg"), '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"><path d="M0 0h1v1H0z"/></svg>');
    writeFileSync(join(root, "fixture.css"), [...originals.keys()].map((family) => `@font-face {font-family:"${family}";src:url("./${family}.woff2") format("woff2");}`).join("\n") + '\n.control {background-image:url("./small.svg");}');
    const result = await build(mergeConfig(config, {
      configFile: false, root, logLevel: "silent",
      build: { write: false, minify: false, emptyOutDir: false },
    }));
    if (Array.isArray(result) || !("output" in result)) throw new Error("Expected one in-memory production bundle");
    const assets = result.output.filter((item) => item.type === "asset");
    const css = assets.filter((item) => item.fileName.endsWith(".css")).map((item) => String(item.source)).join("\n");
    const fonts = assets.filter((item) => item.fileName.endsWith(".woff2"));
    expect(fonts).toHaveLength(2);
    expect(css).not.toMatch(/data:(?:font\/|application\/(?:font|x-font))/);
    for (const [family, bytes] of originals) {
      const font = fonts.find((item) => item.fileName.includes(family))!;
      expect(font).toBeDefined();
      expect(Buffer.from(font.source)).toEqual(bytes);
      expect(css).toContain(font.fileName);
    }
    expect(css).toContain("data:image/svg+xml");
    expect(config.build?.sourcemap).toBe(false);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
