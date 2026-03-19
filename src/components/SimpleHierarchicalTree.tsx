import React from 'react';

interface SimpleTreeProps {
  employerId: number;
  readonly?: boolean;
}

const SimpleHierarchicalTree: React.FC<SimpleTreeProps> = ({ employerId }) => {
  return (
    <div className="p-4 border border-gray-300 rounded">
      <h3 className="font-bold text-green-600">
        ✅ Composant Simple Hiérarchique
      </h3>
      <p>Employeur ID: {employerId}</p>
      <p>Ce composant fonctionne correctement !</p>
    </div>
  );
};

export default SimpleHierarchicalTree;