// Runs before first paint so a dark-mode visitor never sees a light flash.
// Kept as a file rather than an inline <script> so the Content-Security-Policy
// can stay at script-src 'self' with no 'unsafe-inline' escape hatch.
try {
  var saved = localStorage.getItem("taskforge-theme");
  if (saved === "light" || saved === "dark") {
    document.documentElement.setAttribute("data-theme", saved);
  }
} catch (_) {
  // Private browsing can throw on storage access; the app falls back to the
  // OS preference once React mounts.
}
