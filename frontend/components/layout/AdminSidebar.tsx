'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { useLayoutBuilderStore, selectSelectedTable, selectActiveZone, selectActiveFloor } from '@/stores/layoutBuilderStore';
import type { LayoutTable } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import toast from 'react-hot-toast';

export function AdminSidebar() {
  const branchId = useLayoutBuilderStore((s) => s.branchId);
  const isSaving = useLayoutBuilderStore((s) => s.isSaving);
  const activeZone = useLayoutBuilderStore(selectActiveZone);
  const activeFloor = useLayoutBuilderStore(selectActiveFloor);
  const selectedTable = useLayoutBuilderStore(selectSelectedTable);
  
  const addTable = useLayoutBuilderStore((s) => s.addTable);
  const updateTable = useLayoutBuilderStore((s) => s.updateTable);
  const deleteTable = useLayoutBuilderStore((s) => s.deleteTable);
  const setSelectedTableId = useLayoutBuilderStore((s) => s.setSelectedTableId);
  const saveLayoutToApi = useLayoutBuilderStore((s) => s.saveLayoutToApi);
  
  const updateZone = useLayoutBuilderStore((s) => s.updateZone);
  const updateFloor = useLayoutBuilderStore((s) => s.updateFloor);
  const activeZoneId = useLayoutBuilderStore((s) => s.activeZoneId);
  const activeFloorId = useLayoutBuilderStore((s) => s.activeFloorId);

  const [tableNumber, setTableNumber] = useState('');
  const [capacity, setCapacity] = useState('');
  const [shape, setShape] = useState<LayoutTable['shape']>('rect');
  const [zoneName, setZoneName] = useState('');
  const [floorName, setFloorName] = useState('');
  const [canvasWidth, setCanvasWidth] = useState(800);
  const [canvasHeight, setCanvasHeight] = useState(600);

  useEffect(() => {
    if (selectedTable) {
      setTableNumber(selectedTable.table_number);
      setCapacity(String(selectedTable.capacity));
      setShape(selectedTable.shape);
    }
  }, [selectedTable]);

  useEffect(() => {
    if (activeZone) {
      setZoneName(activeZone.name);
      if (activeZone.type === 'outdoor') {
        setCanvasWidth(activeZone.width || 800);
        setCanvasHeight(activeZone.height || 600);
      } else if (activeFloor) {
        setCanvasWidth(activeFloor.width);
        setCanvasHeight(activeFloor.height);
      }
    }
  }, [activeZone, activeFloor]);

  const handleAddTable = useCallback(
    (s: 'round' | 'rect') => {
      if (!activeZone) {
        toast.error('Select a zone first');
        return;
      }
      if (activeZone.type === 'indoor' && !activeFloor) {
        toast.error('Select a floor first');
        return;
      }
      addTable(s);
    },
    [addTable, activeZone, activeFloor]
  );

  const handleSaveProps = useCallback(() => {
    if (!selectedTable) return;
    const cap = parseInt(capacity, 10);
    if (isNaN(cap) || cap < 1 || cap > 100) {
      toast.error('Capacity must be 1–100');
      return;
    }
    if (!tableNumber.trim()) {
      toast.error('Table number is required');
      return;
    }
    updateTable(selectedTable.id, {
      table_number: tableNumber.trim(),
      capacity: cap,
      shape,
    });
    toast.success('Table updated');
  }, [selectedTable, tableNumber, capacity, shape, updateTable]);

  const handleDelete = useCallback(() => {
    if (!selectedTable) return;
    deleteTable(selectedTable.id);
    setSelectedTableId(null);
    toast.success('Table removed');
  }, [selectedTable, deleteTable, setSelectedTableId]);

  const handleSaveLayout = useCallback(async () => {
    if (!branchId) {
      toast.error('Select a branch first');
      return;
    }
    try {
      await saveLayoutToApi(branchId);
      toast.success('Layout saved');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to save layout');
    }
  }, [branchId, saveLayoutToApi]);

  const handleUpdateZoneName = useCallback(() => {
    if (!activeZoneId || !zoneName.trim()) return;
    updateZone(activeZoneId, { name: zoneName.trim() });
    toast.success('Zone renamed');
  }, [activeZoneId, zoneName, updateZone]);

  const handleUpdateFloorName = useCallback(() => {
    if (!activeZoneId || !activeFloorId || !floorName.trim()) return;
    updateFloor(activeZoneId, activeFloorId, { name: floorName.trim() });
    toast.success('Floor renamed');
  }, [activeZoneId, activeFloorId, floorName, updateFloor]);

  const handleUpdateDimensions = useCallback(() => {
    if (!activeZoneId) return;
    const w = Math.max(100, Math.min(5000, canvasWidth));
    const h = Math.max(100, Math.min(5000, canvasHeight));
    
    if (activeZone?.type === 'outdoor') {
      updateZone(activeZoneId, { width: w, height: h });
      toast.success('Dimensions updated');
    } else if (activeFloorId) {
      updateFloor(activeZoneId, activeFloorId, { width: w, height: h });
      toast.success('Dimensions updated');
    }
  }, [activeZoneId, activeFloorId, canvasWidth, canvasHeight, activeZone, updateZone, updateFloor]);

  if (!activeZone) {
    return (
      <aside className="w-72 flex-shrink-0 border-r border-secondary-200 bg-white p-4 flex flex-col gap-4">
        <p className="text-secondary-600 text-sm">No zone selected. Add a zone to start.</p>
      </aside>
    );
  }

  return (
    <aside className="w-72 flex-shrink-0 border-r border-secondary-200 bg-white p-4 flex flex-col gap-4 overflow-y-auto">
      {/* Zone/Floor Info */}
      <div>
        <h3 className="font-semibold text-secondary-900 mb-2">Zone: {activeZone.name}</h3>
        {activeZone.type === 'indoor' && activeFloor && (
          <p className="text-sm text-secondary-600">Floor: {activeFloor.name}</p>
        )}
      </div>

      {/* Zone Name Edit */}
      <div>
        <label className="block text-sm text-secondary-600 mb-1">Zone Name</label>
        <div className="flex gap-2">
          <Input
            value={zoneName}
            onChange={(e) => setZoneName(e.target.value)}
            onBlur={handleUpdateZoneName}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleUpdateZoneName();
            }}
            placeholder="Zone name"
          />
        </div>
      </div>

      {/* Floor Name Edit (indoor only) */}
      {activeZone.type === 'indoor' && activeFloor && (
        <div>
          <label className="block text-sm text-secondary-600 mb-1">Floor Name</label>
          <Input
            value={floorName}
            onChange={(e) => setFloorName(e.target.value)}
            onBlur={handleUpdateFloorName}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleUpdateFloorName();
            }}
            placeholder="Floor name"
          />
        </div>
      )}

      {/* Canvas Dimensions */}
      <div>
        <label className="block text-sm text-secondary-600 mb-1">Canvas Size</label>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-secondary-500 mb-1">Width</label>
            <Input
              type="number"
              min={100}
              max={5000}
              value={canvasWidth}
              onChange={(e) => setCanvasWidth(parseInt(e.target.value, 10) || 800)}
              onBlur={handleUpdateDimensions}
            />
          </div>
          <div>
            <label className="block text-xs text-secondary-500 mb-1">Height</label>
            <Input
              type="number"
              min={100}
              max={5000}
              value={canvasHeight}
              onChange={(e) => setCanvasHeight(parseInt(e.target.value, 10) || 600)}
              onBlur={handleUpdateDimensions}
            />
          </div>
        </div>
      </div>

      {/* Add Table */}
      <div>
        <h3 className="font-semibold text-secondary-900 mb-2">Add Table</h3>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => handleAddTable('rect')}
            className="flex-1"
          >
            Rectangle
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => handleAddTable('round')}
            className="flex-1"
          >
            Round
          </Button>
        </div>
      </div>

      {/* Edit Table */}
      {selectedTable && (
        <div className="border-t border-secondary-200 pt-4">
          <h3 className="font-semibold text-secondary-900 mb-2">Edit Table</h3>
          <div className="space-y-2">
            <label className="block text-sm text-secondary-600">Table number</label>
            <Input
              value={tableNumber}
              onChange={(e) => setTableNumber(e.target.value)}
              placeholder="e.g. T1"
            />
            <label className="block text-sm text-secondary-600">Capacity</label>
            <Input
              type="number"
              min={1}
              max={100}
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
            />
            <label className="block text-sm text-secondary-600">Shape</label>
            <select
              value={shape}
              onChange={(e) => setShape(e.target.value as LayoutTable['shape'])}
              className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm"
            >
              <option value="rect">Rectangle</option>
              <option value="round">Round</option>
            </select>
          </div>
          <div className="flex gap-2 mt-3">
            <Button type="button" variant="primary" onClick={handleSaveProps} className="flex-1">
              Apply
            </Button>
            <Button type="button" variant="secondary" onClick={handleDelete}>
              Delete
            </Button>
          </div>
        </div>
      )}

      {/* Save Button */}
      <div className="mt-auto border-t border-secondary-200 pt-4">
        <Button
          type="button"
          variant="primary"
          onClick={handleSaveLayout}
          disabled={!branchId || isSaving}
          className="w-full"
        >
          {isSaving ? 'Saving…' : 'Save layout'}
        </Button>
      </div>
    </aside>
  );
}
