import React, { useId } from "react";
import { Button, Dialog, Heading, Modal, ModalOverlay } from "react-aria-components";
import { PendingButton } from "./PendingButton";
import "./confirmationAction.css";

export default function ConfirmationDialog({ title, description, confirmLabel, pending, error, onConfirm, onCancel }) {
  const descriptionId = useId();
  return (
    <ModalOverlay className="confirmation-overlay" isKeyboardDismissDisabled={pending}>
      <Modal className="confirmation-modal card">
        <Dialog className="confirmation-dialog" aria-describedby={descriptionId}>
          <Heading slot="title">{title}</Heading>
          <p id={descriptionId}>{description}</p>
          {error && <p role="alert" className="form-error">{error}</p>}
          {pending && <p role="status">Submitting request…</p>}
          <div className="confirmation-actions">
            <Button type="button" className="text-button" autoFocus isDisabled={pending} onPress={onCancel}>Cancel</Button>
            <PendingButton type="button" className="small-button" pending={pending} onPress={onConfirm}>{confirmLabel}</PendingButton>
          </div>
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}
