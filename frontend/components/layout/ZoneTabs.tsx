'use client';

import React from 'react';
import type { LayoutZone } from '@/lib/types';
import { Button } from '@/components/ui/button';

interface ZoneTabsProps {
  zones: LayoutZone[];
  activeZoneId: string | null;
  onSelectZone: (zoneId: string) => void;
  onAddZone: (type: 'indoor' | 'outdoor') => void;
  onDeleteZone: (zoneId: string) => void;
  onRenameZone: (zoneId: string, name: string) => void;
}

export function ZoneTabs({
  zones,
  activeZoneId,
  onSelectZone,
  onAddZone,
  onDeleteZone,
  onRenameZone,
}: ZoneTabsProps) {
  const [editingZoneId, setEditingZoneId] = React.useState<string | null>(null);
  const [editName, setEditName] = React.useState('');

  const handleStartEdit = (zone: LayoutZone) => {
    setEditingZoneId(zone.id);
    setEditName(zone.name);
  };

  const handleSaveEdit = () => {
    if (editingZoneId && editName.trim()) {
      onRenameZone(editingZoneId, editName.trim());
      setEditingZoneId(null);
      setEditName('');
    }
  };

  const handleCancelEdit = () => {
    setEditingZoneId(null);
    setEditName('');
  };

  return (
    <div className="border-b border-secondary-200 bg-white">
      <div className="flex items-center gap-2 px-4 py-2 overflow-x-auto">
        {zones.map((zone) => (
          <div key={zone.id} className="flex items-center gap-1 flex-shrink-0">
            {editingZoneId === zone.id ? (
              <div className="flex items-center gap-1">
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
              </div>
            ) : (
              <button
                onClick={() => onSelectZone(zone.id)}
                onDoubleClick={() => handleStartEdit(zone)}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  activeZoneId === zone.id
                    ? 'bg-primary-600 text-white'
                    : 'bg-secondary-100 text-secondary-700 hover:bg-secondary-200'
                }`}
              >
                {zone.name}
              </button>
            )}
            {zones.length > 1 && (
              <button
                onClick={() => onDeleteZone(zone.id)}
                className="text-red-600 hover:text-red-700 text-sm px-1"
                title="Delete zone"
              >
                ×
              </button>
            )}
          </div>
        ))}
        <div className="flex items-center gap-1 ml-2 flex-shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onAddZone('indoor')}
            className="text-xs"
          >
            + Indoor
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onAddZone('outdoor')}
            className="text-xs"
          >
            + Outdoor
          </Button>
        </div>
      </div>
    </div>
  );
}
