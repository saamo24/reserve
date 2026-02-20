'use client';

import React, { useEffect, useState } from 'react';
import { getBranchTables } from '@/lib/api';
import { TableResponse, BranchResponse } from '@/lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LoadingSpinner } from '@/components/ui/loading';
import { EmptyState } from '@/components/ui/empty-state';
import toast from 'react-hot-toast';

interface TableSelectionProps {
  branch: BranchResponse;
  onTableSelect: (table: TableResponse) => void;
}

export function TableSelection({ branch, onTableSelect }: TableSelectionProps) {
  const [tables, setTables] = useState<TableResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState<TableResponse | null>(null);

  useEffect(() => {
    async function fetchTables() {
      try {
        setIsLoading(true);
        const data = await getBranchTables(branch.id);
        setTables(data);
        if (data.length === 0) {
          toast.error('No tables available for this branch');
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load tables';
        toast.error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    }

    fetchTables();
  }, [branch.id]);

  const handleTableSelect = (table: TableResponse) => {
    setSelectedTable(table);
  };

  const handleContinue = () => {
    if (selectedTable) {
      onTableSelect(selectedTable);
    }
  };

  if (isLoading) {
    return (
      <Card variant="elevated">
        <CardContent className="p-12">
          <div className="flex justify-center">
            <LoadingSpinner size="lg" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (tables.length === 0) {
    return (
      <Card variant="elevated">
        <CardContent className="p-12">
          <EmptyState
            title="No tables available"
            description="There are currently no tables available for this branch. Please contact the restaurant directly."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card variant="elevated">
      <CardHeader>
        <CardTitle>Select a Table</CardTitle>
        <p className="text-sm text-secondary-600 mt-2">
          Choose a table that suits your party size
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {tables.map((table) => (
            <button
              key={table.id}
              onClick={() => handleTableSelect(table)}
              className={`p-4 rounded-xl border-2 transition-all duration-200 text-left ${
                selectedTable?.id === table.id
                  ? 'border-primary-600 bg-primary-50 shadow-md'
                  : 'border-secondary-200 bg-white hover:border-primary-300 hover:shadow-sm'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="font-semibold text-lg text-secondary-900">
                  Table {table.table_number}
                </h3>
                {selectedTable?.id === table.id && (
                  <span className="text-primary-600 text-xl">✓</span>
                )}
              </div>
              <div className="space-y-1 text-sm text-secondary-600">
                <p>Capacity: {table.capacity} guests</p>
                <p>Location: {table.location}</p>
              </div>
            </button>
          ))}
        </div>

        <div className="flex justify-end">
          <Button
            variant="primary"
            onClick={handleContinue}
            disabled={!selectedTable}
            className="min-w-[120px]"
          >
            Continue
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
