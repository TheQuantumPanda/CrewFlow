import { StrictMode, useState } from "react";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Modal } from "./Modal";

interface HarnessProps {
  version?: number;
  onClose?: (version: number) => void;
  openerPresent?: boolean;
  openerDisabled?: boolean;
  mounted?: boolean;
  keepMounted?: boolean;
}

function Harness({ version = 1, onClose, openerPresent = true, openerDisabled = false, mounted = true, keepMounted = false }: HarnessProps) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const close = () => { onClose?.(version); setOpen(false); };

  return (
    <>
      {openerPresent && <button disabled={openerDisabled} onClick={() => setOpen(true)}>Open dialog</button>}
      {mounted && (keepMounted || open) && (
        <Modal open={open} title="Focus fixture" subtitle="Dialog contract" onClose={close}>
          <form aria-label="Fixture form" noValidate onSubmit={(event) => {
            event.preventDefault();
            if (!name.trim()) setError("Name is required");
            else setSaving(true);
          }}>
            {error && <p role="alert">{error}</p>}
            <label>Name<input value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label>Notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
            <button type="button" onClick={close}>Cancel</button>
            <button type="submit" disabled={saving}>{saving ? "Saving…" : "Save"}</button>
          </form>
        </Modal>
      )}
    </>
  );
}

afterEach(() => {
  cleanup();
  document.body.style.overflow = "";
  vi.restoreAllMocks();
});

describe.each([false, true])("Modal lifecycle (StrictMode=%s)", (strict) => {
  function setup(props: HarnessProps = {}) {
    const ui = (next: HarnessProps) => strict ? <StrictMode><Harness {...next} /></StrictMode> : <Harness {...next} />;
    const view = render(ui(props));
    return { ...view, rerenderProps: (next: HarnessProps) => view.rerender(ui(next)), user: userEvent.setup() };
  }

  async function open(user: ReturnType<typeof userEvent.setup>) {
    const opener = screen.getByRole("button", { name: "Open dialog" });
    await user.tab();
    expect(opener).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("dialog", { name: "Focus fixture" })).toHaveAttribute("aria-modal", "true");
    expect(screen.getByRole("textbox", { name: "Name" })).toHaveFocus();
    return opener;
  }

  it("enters the first control and returns to the keyboard opener on Escape", async () => {
    const { user } = setup();
    const opener = await open(user);
    await user.tab();
    expect(screen.getByRole("textbox", { name: "Notes" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("restores focus after the child close button is used", async () => {
    const { user } = setup();
    const opener = await open(user);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(opener).toHaveFocus();
  });

  it("contains Tab and Shift+Tab at both ends", async () => {
    const { user } = setup();
    await open(user);
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Save" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("textbox", { name: "Name" })).toHaveFocus();
  });

  it("keeps focus on parent rerender and invokes the latest close callback", async () => {
    const onClose = vi.fn();
    const { user, rerenderProps } = setup({ version: 1, onClose });
    const opener = await open(user);
    await user.tab();
    rerenderProps({ version: 2, onClose });
    expect(screen.getByRole("textbox", { name: "Notes" })).toHaveFocus();
    expect(document.body.style.overflow).toBe("hidden");
    await user.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledExactlyOnceWith(2);
    expect(opener).toHaveFocus();
  });

  it("does not jump to the first field while typing in a controlled second field", async () => {
    const { user } = setup();
    await open(user);
    await user.tab();
    const notes = screen.getByRole("textbox", { name: "Notes" });
    await user.keyboard("A complete draft");
    expect(notes).toHaveValue("A complete draft");
    expect(notes).toHaveFocus();
    expect(screen.getByRole("textbox", { name: "Name" })).toHaveValue("");
  });

  it("keeps focus through validation rerenders and still cancels", async () => {
    const { user } = setup();
    const opener = await open(user);
    await user.tab();
    fireEvent.submit(screen.getByRole("form", { name: "Fixture form" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Name is required");
    expect(screen.getByRole("textbox", { name: "Notes" })).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(opener).toHaveFocus();
  });

  it("keeps focus while saving and excludes the disabled save button from the trap", async () => {
    const { user } = setup();
    await open(user);
    await user.keyboard("Fixture");
    await user.tab();
    fireEvent.submit(screen.getByRole("form", { name: "Fixture form" }));
    expect(screen.getByRole("button", { name: "Saving…" })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Notes" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Cancel" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("textbox", { name: "Name" })).toHaveFocus();
  });

  it("does not call focus on an opener removed while the dialog is open", async () => {
    const { user, rerenderProps } = setup();
    const opener = await open(user);
    const focus = vi.spyOn(opener, "focus");
    rerenderProps({ openerPresent: false });
    await user.keyboard("{Escape}");
    expect(focus).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not refocus a connected opener that became disabled", async () => {
    const { user, rerenderProps } = setup();
    const opener = await open(user);
    const focus = vi.spyOn(opener, "focus");
    rerenderProps({ openerDisabled: true });
    await user.keyboard("{Escape}");
    expect(opener.isConnected).toBe(true);
    expect(focus).not.toHaveBeenCalled();
  });

  it("restores a connected opener and scroll state on dialog unmount without firing onClose", async () => {
    document.body.style.overflow = "clip";
    const onClose = vi.fn();
    const { user, rerenderProps } = setup({ onClose });
    const opener = await open(user);
    rerenderProps({ onClose, mounted: false });
    expect(opener).toHaveFocus();
    expect(document.body.style.overflow).toBe("clip");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("dismisses only a backdrop mousedown, not interaction inside the dialog", async () => {
    const { user } = setup();
    const opener = await open(user);
    const dialog = screen.getByRole("dialog");
    fireEvent.mouseDown(dialog);
    expect(dialog).toBeInTheDocument();
    fireEvent.mouseDown(dialog.parentElement!);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });

  it("prevents the backdrop's native focus transfer after restoring the opener", async () => {
    const onClose = vi.fn();
    const { user } = setup({ onClose });
    const opener = await open(user);
    const overlay = screen.getByRole("dialog").parentElement!;
    expect(fireEvent.mouseDown(overlay)).toBe(false);
    expect(onClose).toHaveBeenCalledExactlyOnceWith(1);
    expect(opener).toHaveFocus();
  });

  it("preserves pre-existing scroll style across open/close cycles when kept mounted", async () => {
    document.body.style.overflow = "auto";
    const { user } = setup({ keepMounted: true });
    const opener = await open(user);
    expect(document.body.style.overflow).toBe("hidden");
    await user.keyboard("{Escape}");
    expect(document.body.style.overflow).toBe("auto");
    expect(opener).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("textbox", { name: "Name" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(opener).toHaveFocus();
    expect(document.body.style.overflow).toBe("auto");
  });
});
