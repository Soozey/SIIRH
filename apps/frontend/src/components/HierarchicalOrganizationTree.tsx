import type { FC } from "react";
import HierarchicalOrganizationTreeFinal from "./HierarchicalOrganizationTreeFinal";

type HierarchicalTreeProps = {
  employerId: number;
  readonly?: boolean;
  onNodeSelect?: (nodeId: number | null) => void;
  selectedNodeId?: number | null;
};

const HierarchicalOrganizationTree: FC<HierarchicalTreeProps> = (props) => {
  return <HierarchicalOrganizationTreeFinal {...props} />;
};

export default HierarchicalOrganizationTree;
