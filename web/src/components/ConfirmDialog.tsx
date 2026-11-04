import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from "react";

import { Modal } from "./Modal";

interface ConfirmOptions {
  title?: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
}

type Confirm = (options: ConfirmOptions) => Promise<boolean>;

const ConfirmContext = createContext<Confirm | null>(null);

/**
 * Promise-based replacement for window.confirm(), so destructive actions get a
 * focus-trapped dialog that matches the rest of the app instead of a browser
 * alert some mobile browsers suppress entirely.
 */
export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolver = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback<Confirm>((next) => {
    setOptions(next);
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve;
    });
  }, []);

  const settle = useCallback((result: boolean) => {
    setOptions(null);
    resolver.current?.(result);
    resolver.current = null;
  }, []);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Modal
        open={options !== null}
        title={options?.title ?? "Are you sure?"}
        onClose={() => settle(false)}
        width={400}
      >
        <div className="dialog-body">
          <p className="text-sm muted">{options?.message}</p>
        </div>
        <div className="dialog-footer">
          <button type="button" className="btn btn-ghost" onClick={() => settle(false)}>
            Cancel
          </button>
          <button
            type="button"
            className={options?.danger === false ? "btn btn-primary" : "btn btn-danger"}
            onClick={() => settle(true)}
          >
            {options?.confirmLabel ?? "Confirm"}
          </button>
        </div>
      </Modal>
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  const context = useContext(ConfirmContext);
  if (!context) throw new Error("useConfirm must be used inside <ConfirmProvider>");
  return context;
}
