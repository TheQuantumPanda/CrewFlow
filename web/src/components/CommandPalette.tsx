import {
  CornerDownLeft,
  Moon,
  MoveUp,
  Search,
  Sun,
  type LucideIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { NAV_ITEMS } from "../layout/navigation";
import { useTheme } from "../theme";
import { Modal } from "./Modal";

interface Command {
  id: string;
  label: string;
  group: string;
  icon: LucideIcon;
  hint?: string;
  run: () => void;
}

/**
 * Cmd/Ctrl-K palette for navigation and the handful of global actions.
 *
 * Matching is a subsequence test rather than a substring one, so "mt" finds
 * "My Tasks" the way it does in an editor.
 */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { user, can, logout } = useAuth();

  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);

  const commands = useMemo<Command[]>(() => {
    const visible = NAV_ITEMS.filter((item) => !item.permission || can(item.permission));

    const navigation: Command[] = visible.map((item) => ({
      id: `nav:${item.to}`,
      label: item.label,
      group: "Go to",
      icon: item.icon,
      hint: item.shortcut,
      run: () => navigate(item.to),
    }));

    const actions: Command[] = [
      {
        id: "theme",
        label: theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
        group: "Actions",
        icon: theme === "dark" ? Sun : Moon,
        run: toggleTheme,
      },
    ];

    if (user) {
      actions.push({
        id: "logout",
        label: "Sign out",
        group: "Actions",
        icon: MoveUp,
        run: () => {
          void logout().then(() => navigate("/login", { replace: true }));
        },
      });
    }

    return [...navigation, ...actions];
  }, [navigate, theme, toggleTheme, user, logout, can]);

  const results = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return commands;
    return commands.filter((command) => isSubsequence(needle, command.label.toLowerCase()));
  }, [commands, query]);

  // Reset whenever the palette is reopened, so it never shows the last search.
  useEffect(() => {
    if (open) {
      setQuery("");
      setSelected(0);
    }
  }, [open]);

  useEffect(() => {
    setSelected(0);
  }, [query]);

  // Keep the highlighted row in view when arrowing past the fold.
  useEffect(() => {
    listRef.current
      ?.querySelector<HTMLElement>('[data-selected="true"]')
      ?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  const choose = useCallback(
    (command: Command) => {
      onClose();
      command.run();
    },
    [onClose],
  );

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelected((current) => (results.length ? (current + 1) % results.length : 0));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelected((current) =>
        results.length ? (current - 1 + results.length) % results.length : 0,
      );
    } else if (event.key === "Enter") {
      event.preventDefault();
      const command = results[selected];
      if (command) choose(command);
    }
  }

  let lastGroup: string | null = null;

  return (
    <Modal open={open} onClose={onClose} width={560} bare className="palette">
      <div className="palette-input-row">
        <Search />
        <input
          className="palette-input"
          placeholder="Search pages and actions…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Search commands"
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      {results.length === 0 ? (
        <p className="palette-empty">No matches for “{query}”</p>
      ) : (
        <ul className="palette-list" ref={listRef}>
          {results.map((command, index) => {
            const Icon = command.icon;
            const showGroup = command.group !== lastGroup;
            lastGroup = command.group;

            return (
              <li key={command.id}>
                {showGroup ? <div className="palette-group">{command.group}</div> : null}
                <button
                  type="button"
                  className="palette-item"
                  data-selected={index === selected}
                  onClick={() => choose(command)}
                  onMouseMove={() => setSelected(index)}
                >
                  <Icon />
                  <span>{command.label}</span>
                  {command.hint ? <kbd className="palette-item-hint">{command.hint}</kbd> : null}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <div className="palette-footer">
        <span className="palette-hint">
          <kbd>↑</kbd>
          <kbd>↓</kbd> navigate
        </span>
        <span className="palette-hint">
          <kbd>
            <CornerDownLeft size={10} />
          </kbd>
          select
        </span>
        <span className="palette-hint">
          <kbd>esc</kbd> close
        </span>
      </div>
    </Modal>
  );
}

/** True when every character of `needle` appears in order within `haystack`. */
function isSubsequence(needle: string, haystack: string) {
  let index = 0;
  for (const char of haystack) {
    if (char === needle[index]) index++;
    if (index === needle.length) return true;
  }
  return index === needle.length;
}
