'use client';

import React, { useState, useCallback } from 'react';
import { useFloorEditorStore, selectSelectedTable } from '@/stores/floorEditorStore';
import type { LayoutTable } from '@/lib/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import toast from 'react-hot-toast';

export function FloorEditorSidebar() {
  const branchId = useFloorEditorStore((s) => s.branchId);
  const layout = useFloorEditorStore((s) => s.layout);
  const selectedId = useFloorEditorStore((s) => s.selectedId);
  const isSaving = useFloorEditorStore((s) => s.isSaving);
  const addTable = useFloorEditorStore((s) => s.addTable);
  const updateTable = useFloorEditorStore((s) => s.updateTable);
  const deleteTable = useFloorEditorStore((s) => s.deleteTable);
  const saveLayoutToApi = useFloorEditorStore((s) => s.saveLayoutToApi);
  const setSelectedId = useFloorEditorStore((s) => s.setSelectedId);

  const selectedTable = useFloorEditorStore(selectSelectedTable);
  const [tableNumber, setTableNumber] = useState('');
  const [capacity, setCapacity] = useState('');
  const [shape, setShape] = useState<LayoutTable['shape']>('rect');

  React.useEffect(() => {
    if (selectedTable) {
      setTableNumber(selectedTable.table_number);
      setCapacity(String(selectedTable.capacity));
      setShape(selectedTable.shape);
    }
  }, [selectedTable]);

  const handleAddTable = useCallback(
    (s: 'round' | 'rect') => {
      addTable(s);
    },
    [addTable]
  );

  const handleSaveProps = useCallback(() => {
    if (!selectedId || !selectedTable) return;
    const cap = parseInt(capacity, 10);
    if (isNaN(cap) || cap < 1 || cap > 100) {
      toast.error('Capacity must be 1–100');
      return;
    }
    if (!tableNumber.trim()) {
      toast.error('Table number is required');
      return;
    }
    updateTable(selectedId, {
      table_number: tableNumber.trim(),
      capacity: cap,
      shape,
    });
    toast.success('Table updated');
  }, [selectedId, selectedTable, tableNumber, capacity, shape, updateTable]);

  const handleDelete = useCallback(() => {
    if (!selectedId) return;
    deleteTable(selectedId);
    setSelectedId(null);
    toast.success('Table removed');
  }, [selectedId, deleteTable, setSelectedId]);

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

  return (
    <aside className="w-72 flex-shrink-0 border-r border-secondary-200 bg-white p-4 flex flex-col gap-4">
      <div>
        <h3 className="font-semibold text-secondary-900 mb-2">Add table</h3>
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

      {selectedTable && (
        <div className="border-t border-secondary-200 pt-4">
          <h3 className="font-semibold text-secondary-900 mb-2">Edit table</h3>
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
