import React, { useState } from 'react';
import { PlusIcon, XMarkIcon } from "@heroicons/react/24/outline";

interface OrganizationalListInputProps {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder: string;
}

export function OrganizationalListInput({ label, items, onChange, placeholder }: OrganizationalListInputProps) {
  const [newItem, setNewItem] = useState("");

  // S'assurer que items est toujours un tableau de strings
  const safeItems = Array.isArray(items) ? items.filter(item => typeof item === 'string') : [];

  const addItem = () => {
    // S'assurer que newItem est une string
    const itemToAdd = typeof newItem === 'string' ? newItem : String(newItem || '');
    
    if (itemToAdd.trim() && !safeItems.includes(itemToAdd.trim())) {
      const updatedItems = [...safeItems, itemToAdd.trim()];
      onChange(updatedItems);
      safeSetNewItem("");
    }
  };

  // Ensure newItem is always a string
  const safeSetNewItem = (value: any) => {
    const stringValue = typeof value === 'string' ? value : String(value || '');
    setNewItem(stringValue);
  };

  const removeItem = (index: number) => {
    const updatedItems = safeItems.filter((_, i) => i !== index);
    onChange(updatedItems);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addItem();
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      
      {/* Add new item */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={typeof newItem === 'string' ? newItem : ''}
          onChange={(e) => safeSetNewItem(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={placeholder}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
        />
        <button
          type="button"
          onClick={addItem}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <PlusIcon className="h-4 w-4" />
        </button>
      </div>
      
      {/* List of items */}
      <div className="space-y-2 max-h-32 overflow-y-auto">
        {safeItems.map((item, index) => (
          <div key={index} className="flex items-center justify-between bg-white px-3 py-2 rounded-lg border border-gray-200">
            <span className="text-sm text-gray-700">{item}</span>
            <button
              type="button"
              onClick={() => removeItem(index)}
              className="text-red-500 hover:text-red-700 transition-colors"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>
        ))}
        {safeItems.length === 0 && (
          <p className="text-sm text-gray-500 italic">Aucun élément ajouté</p>
        )}
      </div>
    </div>
  );
}