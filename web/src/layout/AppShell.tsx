import { LogOut, Menu, Moon, Search, Sun } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { CommandPalette } from "../components/CommandPalette";
import { CrewFlowBrand } from "../components/Brand";
import { Avatar, ROLE_LABELS } from "../components/ui";
import { useTheme } from "../theme";
import { NAV_ITEMS, metaFor } from "./navigation";

export function AppShell() {
  const { user, can, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  // A route change on mobile should close the drawer, otherwise the new page
  // renders underneath a menu the visitor has to dismiss by hand.
  useEffect(() => setDrawerOpen(false), [location.pathname]);

  useGlobalShortcuts({
    onPalette: () => setPaletteOpen(true),
    onEscape: () => setDrawerOpen(false),
    onGoTo: (key) => {
      const target = NAV_ITEMS.find(
        (item) => item.shortcut?.toLowerCase().endsWith(key) && (!item.permission || can(item.permission)),
      );
      if (target) navigate(target.to);
    },
  });

  const meta = metaFor(location.pathname);
  const employee = user?.employee;
  const displayName = employee ? `${employee.first_name} ${employee.last_name}` : user?.username;

  const visible = NAV_ITEMS.filter((item) => !item.permission || can(item.permission));
  const groups = (["Console", "Workspace"] as const)
    .map((name) => ({ name, items: visible.filter((item) => item.group === name) }))
    .filter((group) => group.items.length > 0);
  const inConsole = location.pathname.startsWith("/admin");

  async function handleLogout() {
    const door = can("console.access") ? "/admin/login" : "/login";
    await logout();
    navigate(door, { replace: true });
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <div
        className={`nav-scrim${drawerOpen ? " visible" : ""}`}
        onClick={() => setDrawerOpen(false)}
        aria-hidden="true"
      />

      <div className={`app-shell${inConsole ? " console" : ""}`}>
        <aside className={`sidebar${drawerOpen ? " open" : ""}`} id="sidebar">
          <div className="brand">
            <CrewFlowBrand />
          </div>

          <nav aria-label="Main">
            {groups.map((group) => (
              <div key={group.name}>
                <div className="nav-group">{group.name}</div>
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end
                      className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
                    >
                      <Icon />
                      <span>{item.label}</span>
                    </NavLink>
                  );
                })}
              </div>
            ))}
          </nav>

          <div className="sidebar-footer">
            <button type="button" className="nav-item theme-control" onClick={toggleTheme}>
              {theme === "dark" ? <Sun /> : <Moon />}
              <span>{theme === "dark" ? "Light theme" : "Dark theme"}</span>
            </button>
            <button type="button" className="nav-item signout-control" onClick={handleLogout}>
              <LogOut />
              <span>Sign out</span>
            </button>

            <div className="sidebar-user">
              <Avatar
                first={employee?.first_name ?? user?.username}
                last={employee?.last_name}
                seed={user?.username}
                size={32}
              />
              <div className="sidebar-user-text">
                <div className="sidebar-user-name" title={displayName}>{displayName}</div>
                <div className="sidebar-user-role">{user ? ROLE_LABELS[user.role] : null}</div>
              </div>
            </div>
          </div>
        </aside>

        <div className="main">
          <header className="topbar">
            <button
              type="button"
              className="nav-toggle"
              onClick={() => setDrawerOpen((open) => !open)}
              aria-expanded={drawerOpen}
              aria-controls="sidebar"
              aria-label="Toggle navigation"
            >
              <Menu size={16} />
            </button>

            <div className="topbar-title" key={location.pathname}>
              <h1>{meta.title}</h1>
              {meta.subtitle ? <p className="topbar-sub">{meta.subtitle}</p> : null}
            </div>

            <div className="topbar-spacer" />

            <button
              type="button"
              className="search-trigger"
              onClick={() => setPaletteOpen(true)}
              aria-label="Open command palette"
            >
              <Search />
              <span>Search…</span>
              <kbd>{isApplePlatform() ? "⌘K" : "Ctrl K"}</kbd>
            </button>
          </header>

          <main className="page" id="main" key={location.pathname}>
            <Outlet />
          </main>
        </div>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
}

function isApplePlatform() {
  return /Mac|iPhone|iPad/.test(navigator.platform ?? "");
}

/** How long a pending `g` waits for its second key before lapsing. */
const CHORD_TIMEOUT_MS = 1200;

/**
 * Global shortcuts: Cmd/Ctrl-K for the palette, and `g` followed by a letter
 * to jump between sections.
 *
 * Every handler ignores keystrokes aimed at a text field, so typing "g" into
 * a search box neither swallows the character nor arms a chord.
 */
function useGlobalShortcuts({
  onPalette,
  onEscape,
  onGoTo,
}: {
  onPalette: () => void;
  onEscape: () => void;
  onGoTo: (key: string) => void;
}) {
  const handlers = useRef({ onPalette, onEscape, onGoTo });
  handlers.current = { onPalette, onEscape, onGoTo };

  useEffect(() => {
    let chordArmed = false;
    let chordTimer = 0;

    function disarm() {
      chordArmed = false;
      window.clearTimeout(chordTimer);
    }

    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target instanceof HTMLSelectElement ||
        target?.isContentEditable === true;

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        disarm();
        handlers.current.onPalette();
        return;
      }

      if (typing || event.metaKey || event.ctrlKey || event.altKey) return;

      if (event.key === "Escape") {
        disarm();
        handlers.current.onEscape();
        return;
      }

      if (chordArmed) {
        disarm();
        handlers.current.onGoTo(event.key.toLowerCase());
        return;
      }

      if (event.key.toLowerCase() === "g") {
        chordArmed = true;
        // Lapse on its own, so a stray `g` cannot hijack the next keystroke
        // minutes later.
        chordTimer = window.setTimeout(disarm, CHORD_TIMEOUT_MS);
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      window.clearTimeout(chordTimer);
    };
  }, []);
}
