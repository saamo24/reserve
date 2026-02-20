'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { listTables, createTable, updateTable, deleteTable, listBranches } from '@/lib/api';
import { TableResponse, TableCreate, TableUpdate, TableLocation, BranchResponse } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { LoadingPage } from '@/components/ui/loading';
import { EmptyState } from '@/components/ui/empty-state';
import toast from 'react-hot-toast';

export default function TablesPage() {
  const [tables, setTables] = useState<TableResponse[]>([]);
  const [branches, setBranches] = useState<BranchResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedBranch, setSelectedBranch] = useState<string>('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTable, setEditingTable] = useState<TableResponse | null>(null);
  const [formData, setFormData] = useState<TableCreate>({
    branch_id: '',
    table_number: '',
    capacity: 4,
    location: TableLocation.INDOOR,
    is_active: true,
  });

  useEffect(() => {
    fetchBranches();
  }, []);

  async function fetchBranches() {
    try {
      const response = await listBranches({ page_size: 100 });
      setBranches(response.data);
    } catch (err) {
      console.error('Failed to load branches:', err);
    }
  }

  const fetchTables = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: any = { page_size: 100 };
      if (selectedBranch) params.branch_id = selectedBranch;
      const response = await listTables(params);
      setTables(response.data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load tables';
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  }, [selectedBranch]);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingTable) {
        await updateTable(editingTable.id, formData as TableUpdate);
        toast.success('Table updated successfully');
      } else {
        await createTable(formData);
        toast.success('Table created successfully');
      }
      setIsModalOpen(false);
      setEditingTable(null);
      setFormData({
        branch_id: selectedBranch || '',
        table_number: '',
        capacity: 4,
        location: TableLocation.INDOOR,
        is_active: true,
      });
      fetchTables();
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Operation failed';
      toast.error(errorMessage);
    }
  };

  const handleEdit = (table: TableResponse) => {
    setEditingTable(table);
    setFormData({
      branch_id: table.branch_id,
      table_number: table.table_number,
      capacity: table.capacity,
      location: table.location,
      is_active: table.is_active,
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this table?')) {
      return;
    }

    try {
      await deleteTable(id);
      toast.success('Table deleted successfully');
      fetchTables();
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || 'Failed to delete table';
      toast.error(errorMessage);
    }
  };

  const handleCreate = () => {
    setEditingTable(null);
    setFormData({
      branch_id: selectedBranch || '',
      table_number: '',
      capacity: 4,
      location: TableLocation.INDOOR,
      is_active: true,
    });
    setIsModalOpen(true);
  };

  if (isLoading) {
    return <LoadingPage />;
  }

  const locationOptions = [
    { value: TableLocation.INDOOR, label: 'Indoor' },
    { value: TableLocation.OUTDOOR, label: 'Outdoor' },
    { value: TableLocation.VIP, label: 'VIP' },
  ];

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">Tables</h1>
          <p className="text-secondary-600 mt-2">Manage restaurant tables</p>
        </div>
        <Button variant="primary" onClick={handleCreate} disabled={!selectedBranch}>
          + Create Table
        </Button>
      </div>

      <Card variant="elevated" className="mb-6">
        <CardContent className="p-4">
          <Select
            label="Filter by Branch"
            value={selectedBranch}
            onChange={(e) => setSelectedBranch(e.target.value)}
            options={[
              { value: '', label: 'All Branches' },
              ...branches.map((b) => ({ value: b.id, label: b.name })),
            ]}
          />
        </CardContent>
      </Card>

      {tables.length === 0 ? (
        <EmptyState
          title="No tables found"
          description={
            selectedBranch
              ? 'Create your first table for this branch'
              : 'Select a branch or create tables'
          }
          actionLabel="Create Table"
          onAction={handleCreate}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tables.map((table) => {
            const branch = branches.find((b) => b.id === table.branch_id);
            return (
              <Card key={table.id} variant="elevated">
                <CardContent className="p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-semibold text-secondary-900 mb-1">
                        Table {table.table_number}
                      </h3>
                      <p className="text-sm text-secondary-600">{branch?.name || 'Unknown Branch'}</p>
                    </div>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${
                        table.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {table.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm text-secondary-600 mb-4">
                    <p>Capacity: {table.capacity} guests</p>
                    <p>Location: {table.location}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => handleEdit(table)}>
                      Edit
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => handleDelete(table.id)}>
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <Card variant="elevated" className="w-full max-w-md">
            <CardHeader>
              <CardTitle>{editingTable ? 'Edit Table' : 'Create Table'}</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <Select
                  label="Branch"
                  value={formData.branch_id}
                  onChange={(e) => setFormData({ ...formData, branch_id: e.target.value })}
                  options={branches.map((b) => ({ value: b.id, label: b.name }))}
                  required
                  disabled={!!editingTable}
                />
                <Input
                  label="Table Number"
                  value={formData.table_number}
                  onChange={(e) => setFormData({ ...formData, table_number: e.target.value })}
                  required
                />
                <Input
                  label="Capacity"
                  type="number"
                  value={formData.capacity}
                  onChange={(e) =>
                    setFormData({ ...formData, capacity: parseInt(e.target.value) })
                  }
                  min={1}
                  max={100}
                  required
                />
                <Select
                  label="Location"
                  value={formData.location}
                  onChange={(e) =>
                    setFormData({ ...formData, location: e.target.value as TableLocation })
                  }
                  options={locationOptions}
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
                      setEditingTable(null);
                    }}
                  >
                    Cancel
                  </Button>
                  <Button type="submit" variant="primary">
                    {editingTable ? 'Update' : 'Create'}
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
