'use client';

import React, { useEffect, useState } from 'react';
import { listBranches, createBranch, updateBranch } from '@/lib/api';
import { BranchResponse, BranchCreate, BranchUpdate } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { LoadingPage } from '@/components/ui/loading';
import { EmptyState } from '@/components/ui/empty-state';
import toast from 'react-hot-toast';

export default function BranchesPage() {
  const [branches, setBranches] = useState<BranchResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBranch, setEditingBranch] = useState<BranchResponse | null>(null);
  const [formData, setFormData] = useState<BranchCreate>({
    name: '',
    address: '',
    opening_time: '09:00',
    closing_time: '22:00',
    slot_duration_minutes: 120,
    is_active: true,
  });

  useEffect(() => {
    fetchBranches();
  }, []);

  async function fetchBranches() {
    try {
      setIsLoading(true);
      const response = await listBranches({ page_size: 100 });
      setBranches(response.data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load branches';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingBranch) {
        await updateBranch(editingBranch.id, formData as BranchUpdate);
        toast.success('Branch updated successfully');
      } else {
        await createBranch(formData);
        toast.success('Branch created successfully');
      }
      setIsModalOpen(false);
      setEditingBranch(null);
      setFormData({
        name: '',
        address: '',
        opening_time: '09:00',
        closing_time: '22:00',
        slot_duration_minutes: 120,
        is_active: true,
      });
      fetchBranches();
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Operation failed';
      toast.error(errorMessage);
    }
  };

  const handleEdit = (branch: BranchResponse) => {
    setEditingBranch(branch);
    setFormData({
      name: branch.name,
      address: branch.address,
      opening_time: branch.opening_time.substring(0, 5),
      closing_time: branch.closing_time.substring(0, 5),
      slot_duration_minutes: branch.slot_duration_minutes,
      is_active: branch.is_active,
    });
    setIsModalOpen(true);
  };

  const handleCreate = () => {
    setEditingBranch(null);
    setFormData({
      name: '',
      address: '',
      opening_time: '09:00',
      closing_time: '22:00',
      slot_duration_minutes: 120,
      is_active: true,
    });
    setIsModalOpen(true);
  };

  if (isLoading) {
    return <LoadingPage />;
  }

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">Branches</h1>
          <p className="text-secondary-600 mt-2">Manage restaurant branches</p>
        </div>
        <Button variant="primary" onClick={handleCreate}>
          + Create Branch
        </Button>
      </div>

      {branches.length === 0 ? (
        <EmptyState
          title="No branches found"
          description="Create your first branch to get started"
          actionLabel="Create Branch"
          onAction={handleCreate}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {branches.map((branch) => (
            <Card key={branch.id} variant="elevated">
              <CardContent className="p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="text-xl font-semibold text-secondary-900 mb-1">
                      {branch.name}
                    </h3>
                    <p className="text-sm text-secondary-600">{branch.address}</p>
                  </div>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      branch.is_active
                        ? 'bg-green-100 text-green-700'
                        : 'bg-red-100 text-red-700'
                    }`}
                  >
                    {branch.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="space-y-2 text-sm text-secondary-600 mb-4">
                  <p>
                    Hours: {branch.opening_time.substring(0, 5)} -{' '}
                    {branch.closing_time.substring(0, 5)}
                  </p>
                  <p>Slot Duration: {branch.slot_duration_minutes} minutes</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => handleEdit(branch)}>
                  Edit
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card variant="elevated" className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <CardHeader>
              <CardTitle>{editingBranch ? 'Edit Branch' : 'Create Branch'}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <Input
                  label="Name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
                <Input
                  label="Address"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  required
                />
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Opening Time"
                    type="time"
                    value={formData.opening_time}
                    onChange={(e) => setFormData({ ...formData, opening_time: e.target.value })}
                    required
                  />
                  <Input
                    label="Closing Time"
                    type="time"
                    value={formData.closing_time}
                    onChange={(e) => setFormData({ ...formData, closing_time: e.target.value })}
                    required
                  />
                </div>
                <Input
                  label="Slot Duration (minutes)"
                  type="number"
                  value={formData.slot_duration_minutes}
                  onChange={(e) =>
                    setFormData({ ...formData, slot_duration_minutes: parseInt(e.target.value) })
                  }
                  min={15}
                  max={480}
                  required
                />
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="mr-2"
                  />
                  <label htmlFor="is_active" className="text-sm text-secondary-700">
                    Active
                  </label>
                </div>
                <div className="flex justify-end gap-4 pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setIsModalOpen(false);
                      setEditingBranch(null);
                    }}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary">
                    {editingBranch ? 'Update' : 'Create'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
