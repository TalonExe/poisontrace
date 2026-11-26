import React, { lazy, Suspense, useRef, useState } from "react";
import { Button, DialogTrigger } from "react-aria-components";

const ConfirmationDialog = lazy(() => import("./ConfirmationDialog"));

export function ConfirmationAction({
  children, className = "text-button", triggerLabel, disabled,
  title, description, confirmLabel, errorMessage, onConfirm, onSuccess,
}) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);

  function changeOpen(next) {
    if (inFlight.current) return;
    setError("");
    setOpen(next);
  }

  async function confirm() {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    setError("");
    try {
      await onConfirm();
      setOpen(false);
      onSuccess?.();
    } catch (failure) {
      setError(errorMessage || failure.message || "Could not complete the request. Try again.");
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  }

  return (
    <DialogTrigger isOpen={open} onOpenChange={changeOpen}>
      <Button type="button" className={className} aria-label={triggerLabel} isDisabled={disabled}>{children}</Button>
      {open && <Suspense fallback={null}>
        <ConfirmationDialog title={title} description={description} confirmLabel={confirmLabel}
          pending={pending} error={error} onConfirm={confirm} onCancel={() => changeOpen(false)} />
      </Suspense>}
    </DialogTrigger>
  );
}
