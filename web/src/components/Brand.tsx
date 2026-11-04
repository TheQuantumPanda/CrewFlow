/** Original CrewFlow mark. The standalone SVG is the single geometry source. */
export function BrandMark({ size = 34, label }: { size?: number; label?: string }) {
  return (
    <svg
      className="brand-mark"
      width={size}
      height={size}
      style={{ width: size, height: size }}
      viewBox="0 0 64 64"
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      focusable="false"
    >
      <use href="/brand/crewflow-icon.svg#crewflow-mark" />
    </svg>
  );
}

/** Horizontal icon + live wordmark; uses the bundled Bricolage font. */
export function CrewFlowBrand() {
  return (
    <span className="brand-lockup">
      <BrandMark />
      <span>CrewFlow</span>
    </span>
  );
}
