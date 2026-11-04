/** Presentation helpers shared across screens. No React, so they're trivially testable. */

export function initials(first?: string | null, last?: string | null) {
  return `${(first ?? "?").charAt(0)}${(last ?? "").charAt(0)}`.toUpperCase() || "?";
}

/** Maps a status onto a class-safe slug, e.g. "In Progress" -> InProgress. */
export function statusSlug(value?: string | null) {
  return String(value ?? "").replace(/\s+/g, "");
}

/** Maps a status or priority onto its badge class, e.g. "In Progress" -> badge-InProgress. */
export function badgeClass(value?: string | null) {
  return `badge-${statusSlug(value)}`;
}

export function relativeTime(iso?: string | null) {
  if (!iso) return "";
  // The API serialises naive UTC timestamps; without the marker the browser
  // reads them as local time and every entry looks hours in the future.
  const utc = /[Z+]|-\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`;
  const then = new Date(utc).getTime();
  if (Number.isNaN(then)) return "";

  const minutes = Math.round((Date.now() - then) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;

  return new Date(utc).toLocaleDateString();
}

/** A stable CrewFlow tone per person; the existing seed remains deterministic. */
export function avatarStyle(seed?: string | null) {
  let hash = 0;
  for (const char of String(seed ?? "?")) hash = (hash * 31 + char.charCodeAt(0)) % 360;
  return {
    background: `var(--avatar-${hash % 6})`,
  };
}

export function fullName(person?: { first_name?: string; last_name?: string } | null) {
  if (!person) return "Unassigned";
  return `${person.first_name ?? ""} ${person.last_name ?? ""}`.trim() || "Unassigned";
}

export function pluralise(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}
