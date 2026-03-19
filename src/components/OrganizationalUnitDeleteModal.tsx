import React from "react";

import SimpleOrganizationalDeleteModal from "./SimpleOrganizationalDeleteModal";

interface OrganizationalUnitDeleteModalProps {
  open?: boolean;
  visible?: boolean;
  unitId: number | null;
  onClose?: () => void;
  onCancel?: () => void;
  onSuccess: () => void;
}

const OrganizationalUnitDeleteModal: React.FC<OrganizationalUnitDeleteModalProps> = ({
  open,
  visible,
  unitId,
  onClose,
  onCancel,
  onSuccess,
}) => {
  const isOpen = open ?? visible ?? false;
  const handleClose = onClose ?? onCancel ?? (() => {});

  return (
    <SimpleOrganizationalDeleteModal
      isOpen={isOpen}
      unitId={unitId}
      onClose={handleClose}
      onSuccess={onSuccess}
    />
  );
};

export default OrganizationalUnitDeleteModal;
