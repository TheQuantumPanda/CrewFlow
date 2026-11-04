import { useEffect, useId, useLayoutEffect, useRef, type ReactNode } from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

interface ModalProps {
  open: boolean;
  title?: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
  width?: number;
  /** Drops the chrome so a bare surface (the command palette) can use the same shell. */
  bare?: boolean;
  className?: string;
}

/**
 * Accessible dialog: labelled, Escape-closable, and focus-trapped.
 *
 * The trap matters — without it Tab walks out of the dialog into the page
 * behind, which for a keyboard or screen-reader user means the dialog is
 * effectively unusable even though it looks fine.
 */
export function Modal({
  open,
  title,
  subtitle,
  onClose,
  children,
  width = 520,
  bare = false,
  className = "",
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  const titleId = useId();

  useLayoutEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    if (!open) return;

    // Own focus for this opening; callback-only rerenders must not recapture it.
    const returnFocusTo = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    const node = dialogRef.current;
    node?.querySelector<HTMLElement>(FOCUSABLE)?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !node) return;

      const focusable = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      if (
        returnFocusTo?.isConnected &&
        !returnFocusTo.matches(':disabled, [aria-disabled="true"]') &&
        !returnFocusTo.closest("[hidden], [inert]")
      ) {
        returnFocusTo.focus();
      }
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          // Dismiss without the native mousedown moving focus after cleanup.
          event.preventDefault();
          onClose();
        }
      }}
    >
      <div
        className={`dialog ${className}`.trim()}
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-label={title ? undefined : "Dialog"}
        style={{ maxWidth: width }}
      >
        {bare ? (
          children
        ) : (
          <>
            <header className="dialog-header">
              <h2 id={titleId}>{title}</h2>
              {subtitle ? <p className="dialog-sub">{subtitle}</p> : null}
            </header>
            {children}
          </>
        )}
      </div>
    </div>
  );
}
