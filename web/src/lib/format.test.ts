import { afterEach, describe, expect, it, vi } from "vitest";

import { avatarStyle, badgeClass, initials, pluralise, relativeTime } from "./format";

afterEach(() => {
  vi.useRealTimers();
});

describe("relativeTime", () => {
  /**
   * The API serialises naive UTC timestamps with no zone marker. Reading one
   * as local time puts every entry hours in the future, which shows up as
   * "just now" on everything — so the marker has to be added back.
   */
  it("treats an unmarked timestamp as UTC", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));

    expect(relativeTime("2026-01-01T11:00:00")).toBe("1h ago");
  });

  it("respects a timestamp that already names its zone", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));

    expect(relativeTime("2026-01-01T11:30:00Z")).toBe("30m ago");
    expect(relativeTime("2026-01-01T11:00:00+00:00")).toBe("1h ago");
  });

  it("collapses the last minute to 'just now'", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));

    expect(relativeTime("2026-01-01T11:59:40")).toBe("just now");
  });

  it("switches to days, then to a date", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-10T12:00:00Z"));

    expect(relativeTime("2026-01-08T12:00:00")).toBe("2d ago");
    expect(relativeTime("2025-11-01T12:00:00")).toMatch(/\d/);
  });

  it("returns an empty string for missing or unparseable input", () => {
    expect(relativeTime(null)).toBe("");
    expect(relativeTime(undefined)).toBe("");
    expect(relativeTime("not a date")).toBe("");
  });
});

describe("badgeClass", () => {
  it("strips the space so 'In Progress' maps to one class", () => {
    expect(badgeClass("In Progress")).toBe("badge-InProgress");
    expect(badgeClass("On Hold")).toBe("badge-OnHold");
  });

  it("handles a missing value", () => {
    expect(badgeClass(null)).toBe("badge-");
  });
});

describe("initials", () => {
  it("takes the first letter of each name", () => {
    expect(initials("Aarav", "Sharma")).toBe("AS");
  });

  it("copes with a missing surname", () => {
    expect(initials("Aarav")).toBe("A");
  });

  it("falls back rather than rendering an empty circle", () => {
    expect(initials(null, null)).toBe("?");
  });
});

describe("avatarStyle", () => {
  it("is stable for the same seed, so a colour does not change on reload", () => {
    expect(avatarStyle("aarav@example.com")).toEqual(avatarStyle("aarav@example.com"));
  });

  it("differs between people", () => {
    expect(avatarStyle("aarav@example.com")).not.toEqual(avatarStyle("rohan@example.com"));
  });
});

describe("pluralise", () => {
  it("uses the singular for exactly one", () => {
    expect(pluralise(1, "person", "people")).toBe("1 person");
    expect(pluralise(0, "person", "people")).toBe("0 people");
    expect(pluralise(3, "task")).toBe("3 tasks");
  });
});
