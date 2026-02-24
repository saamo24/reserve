'use client';

import React from 'react';
import type { LayoutFloor } from '@/lib/types';
import { Button } from '@/components/ui/button';

interface FloorTabsProps {
  floors: LayoutFloor[];
  activeFloorId: string | null;
  onSelectFloor: (floorId: string) => void;
  onAddFloor: () => void;
  onDeleteFloor: (floorId: string) => void;
  onRenameFloor: (floorId: string, name: string) => void;
}

export function FloorTabs({
  floors,
  activeFloorId,
  onSelectFloor,
  onAddFloor,
  onDeleteFloor,
  onRenameFloor,
}: FloorTabsProps) {
  const [editingFloorId, setEditingFloorId] = React.useState<string | null>(null);
  const [editName, setEditName] = React.useState('');

  const handleStartEdit = (floor: LayoutFloor) => {
    setEditingFloorId(floor.id);
    setEditName(floor.name);
  };

  const handleSaveEdit = () => {
    if (editingFloorId && editName.trim()) {
      onRenameFloor(editingFloorId, editName.trim());
      setEditingFloorId(null);
      setEditName('');
    }
  };

  const handleCancelEdit = () => {
    setEditingFloorId(null);
    setEditName('');
  };

  if (floors.length === 0) return null;

  return (
    <div className="border-b border-secondary-200 bg-secondary-50">
      <div className="flex items-center gap-2 px-4 py-2 overflow-x-auto">
        {floors.map((floor) => (
          <div key={floor.id} className="flex items-center gap-1 flex-shrink-0">
            {editingFloorId === floor.id ? (
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={handleSaveEdit}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveEdit();
                  if (e.key === 'Escape') handleCancelEdit();
                }}
                className="px-2 py-1 text-sm border border-secondary-300 rounded focus:outline-none focus:ring-2 focus:ring-primary-500"
                autoFocus
              />
            ) : (
              <button
                onClick={() => onSelectFloor(floor.id)}
                onDoubleClick={() => handleStartEdit(floor)}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  activeFloorId === floor.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-white text-secondary-700 hover:bg-secondary-100'
                }`}
              >
                {floor.name}
              </button>
            )}
            {floors.length > 1 && (
              <button
                onClick={() => onDeleteFloor(floor.id)}
                className="text-red-600 hover:text-red-700 text-sm px-1"
                title="Delete floor"
              >
                ×
              </button>
            )}
          </div>
        ))}
        <Button
          variant="outline"
          size="sm"
          onClick={onAddFloor}
          className="text-xs ml-2 flex-shrink-0"
        >
          + Floor
        </Button>
      </div>
    </div>
  );
}
