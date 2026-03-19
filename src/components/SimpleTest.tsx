import React from 'react';

const SimpleTest: React.FC = () => {
  return (
    <div className="p-8 bg-green-50 border border-green-200 rounded-lg">
      <h1 className="text-2xl font-bold text-green-800 mb-4">✅ React fonctionne !</h1>
      <p className="text-green-700">
        Si vous voyez ce message, React se charge correctement.
      </p>
      <div className="mt-4 p-4 bg-white rounded border">
        <h2 className="font-semibold mb-2">Tests de base :</h2>
        <ul className="space-y-1 text-sm">
          <li>✅ Import React</li>
          <li>✅ Composant fonctionnel</li>
          <li>✅ Classes Tailwind</li>
          <li>✅ Rendu JSX</li>
        </ul>
      </div>
    </div>
  );
};

export default SimpleTest;