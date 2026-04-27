import React from "react";

import SimpleOrganizationalUnitManager from "./SimpleOrganizationalUnitManager";

interface OrganizationalUnitManagerProps {
  employerId: number;
  onRefresh?: () => void;
}

const OrganizationalUnitManager: React.FC<OrganizationalUnitManagerProps> = ({
  employerId,
  onRefresh,
}) => {
  return (
    <SimpleOrganizationalUnitManager
      employerId={employerId}
      onRefresh={onRefresh}
    />
  );
};

export default OrganizationalUnitManager;
