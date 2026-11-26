import React from "react";
import { Button } from "react-aria-components";

export function PendingButton({ pending, disabled, ...props }) {
  return <Button {...props} isDisabled={disabled && !pending} isPending={pending} />;
}
