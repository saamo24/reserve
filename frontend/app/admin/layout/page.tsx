'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { listBranches } from '@/lib/api';
import type { BranchResponse } from '@/lib/types';
import { useFloorEditorStore } from '@/stores/floorEditorStore';
import { LoadingSpinner } from '@/components/ui/loading';
import toast from 'react-hot-toast';

const FloorEditorView = dynamic(
  () =>
    import('@/components/floor/FloorEditorView').then((m) => ({ default: m.FloorEditorView })),
  { ssr: false }
);

export default function AdminLayoutPage() {
  const [branches, setBranches] = useState<BranchResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const branchId = useFloorEditorStore((s) => s.branchId);
  const setBranchId = useFloorEditorStore((s) => s.setBranchId);
  const loadLayout = useFloorEditorStore((s) => s.loadLayout);

  useEffect(() => {
    listBranches({ page_size: 100 })
      .then((res) => setBranches(res.data))
      .catch(() => toast.error('Failed to load branches'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (branchId) {
      loadLayout(branchId);
    }
  }, [branchId, loadLayout]);

  const handleBranchChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value || null;
    setBranchId(id);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Floor plan layout</h1>
        <p className="text-secondary-600 mt-1">
          Drag, resize, and rotate tables. Save to store the layout for this branch.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <label className="text-sm font-medium text-secondary-700">Branch</label>
        <select
          value={branchId ?? ''}
          onChange={handleBranchChange}
          className="rounded-lg border border-secondary-300 px-3 py-2 text-sm min-w-[200px]"
        >
          <option value="">Select a branch</option>
          {branches.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
      </div>
      {branchId ? (
        <div className="border border-secondary-200 rounded-xl overflow-hidden bg-white h-[640px] flex flex-col">
          <FloorEditorView />
        </div>
      ) : (
        <div className="border border-secondary-200 rounded-xl bg-secondary-50 min-h-[400px] flex items-center justify-center text-secondary-600">
          Select a branch to edit the floor plan
        </div>
      )}
    </div>
  );
}
