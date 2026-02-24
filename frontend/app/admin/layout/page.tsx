'use client';

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { listBranches } from '@/lib/api';
import type { BranchResponse } from '@/lib/types';
import { useLayoutBuilderStore } from '@/stores/layoutBuilderStore';
import { LoadingSpinner } from '@/components/ui/loading';
import toast from 'react-hot-toast';

const LayoutManager = dynamic(
  () =>
    import('@/components/layout/LayoutManager').then((m) => ({ default: m.LayoutManager })),
  { ssr: false }
);

export default function AdminLayoutPage() {
  const [branches, setBranches] = useState<BranchResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const branchId = useLayoutBuilderStore((s) => s.branchId);
  const setBranchId = useLayoutBuilderStore((s) => s.setBranchId);
  const loadLayout = useLayoutBuilderStore((s) => s.loadLayout);

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
    <div className="space-y-4 h-full flex flex-col">
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Floor plan layout</h1>
        <p className="text-secondary-600 mt-1">
          Create zones, add floors, and place tables. Drag, resize, and rotate tables. Save to store the layout.
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
        <div className="border border-secondary-200 rounded-xl overflow-hidden bg-white flex-1 min-h-[640px] flex flex-col">
          <LayoutManager />
        </div>
      ) : (
        <div className="border border-secondary-200 rounded-xl bg-secondary-50 min-h-[400px] flex items-center justify-center text-secondary-600">
          Select a branch to edit the floor plan
        </div>
      )}
    </div>
  );
}
