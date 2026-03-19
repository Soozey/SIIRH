import React from "react";

import { HierarchyManagerModalEnhanced } from "./HierarchyManagerModalEnhanced";

interface HierarchyManagerModalProps {
  employerId: number;
  isOpen?: boolean;
  visible?: boolean;
  onClose?: () => void;
  onCancel?: () => void;
  onSave?: () => void;
  onSuccess?: () => void;
  editUnitId?: number | null;
}

export const HierarchyManagerModal: React.FC<HierarchyManagerModalProps> = ({
  employerId,
  isOpen,
  visible,
  onClose,
  onCancel,
  onSave,
  onSuccess,
}) => {
  const modalOpen = isOpen ?? visible ?? false;
  const handleClose = onClose ?? onCancel ?? (() => {});
  const handleSave = onSave ?? onSuccess;

  return (
    <HierarchyManagerModalEnhanced
      employerId={employerId}
      isOpen={modalOpen}
      onClose={handleClose}
      onSave={handleSave}
    />
  );
};

export default HierarchyManagerModal;
