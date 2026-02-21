'use client';

import React, { useEffect, useState } from 'react';
import { listReservations, updateReservation, listBranches } from '@/lib/api';
import { ReservationResponse, ReservationStatus, BranchResponse } from '@/lib/types';
import { ReservationTable } from '@/components/ReservationTable';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { LoadingPage } from '@/components/ui/loading';
import { EmptyState } from '@/components/ui/empty-state';
import toast from 'react-hot-toast';

export default function ReservationsPage() {
  const [reservations, setReservations] = useState<ReservationResponse[]>([]);
  const [branches, setBranches] = useState<BranchResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    branch_id: '',
    date: '',
    status: '',
    phone_number: '',
  });

  useEffect(() => {
    async function fetchBranches() {
      try {
        const response = await listBranches({ page_size: 100 });
        setBranches(response.data);
      } catch (err) {
        console.error('Failed to load branches:', err);
      }
    }

    fetchBranches();
  }, []);

  useEffect(() => {
    async function fetchReservations() {
      try {
        setIsLoading(true);
        const params: any = {
          page,
          page_size: 20,
        };

        if (filters.branch_id) params.branch_id = filters.branch_id;
        if (filters.date) params.date = filters.date;
        if (filters.status) params.status = filters.status as ReservationStatus;
        if (filters.phone_number) params.phone_number = filters.phone_number;

        const response = await listReservations(params);
        setReservations(response.data);
        setTotalPages(Math.ceil(response.meta.total / response.meta.page_size));
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load reservations';
        toast.error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    }

    fetchReservations();
  }, [page, filters]);

  const handleStatusUpdate = async (id: string, status: ReservationStatus) => {
    await updateReservation(id, { status });
    // Refresh reservations
    const params: any = { page, page_size: 20 };
    if (filters.branch_id) params.branch_id = filters.branch_id;
    if (filters.date) params.date = filters.date;
    if (filters.status) params.status = filters.status as ReservationStatus;
    if (filters.phone_number) params.phone_number = filters.phone_number;

    const response = await listReservations(params);
    setReservations(response.data);
  };

  const handleDelete = async (id: string) => {
    // Note: Backend doesn't have delete endpoint, so we'll just update status to cancelled
    await updateReservation(id, { status: ReservationStatus.CANCELLED });
    // Refresh reservations
    const params: any = { page, page_size: 20 };
    if (filters.branch_id) params.branch_id = filters.branch_id;
    if (filters.date) params.date = filters.date;
    if (filters.status) params.status = filters.status as ReservationStatus;
    if (filters.phone_number) params.phone_number = filters.phone_number;

    const response = await listReservations(params);
    setReservations(response.data);
  };

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({
      branch_id: '',
      date: '',
      status: '',
      phone_number: '',
    });
    setPage(1);
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-secondary-900">Reservations</h1>
        <p className="text-secondary-600 mt-2">Manage all restaurant reservations</p>
      </div>

      <Card variant="elevated" className="mb-6">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <Select
              label="Branch"
              value={filters.branch_id}
              onChange={(e) => handleFilterChange('branch_id', e.target.value)}
              options={[
                { value: '', label: 'All Branches' },
                ...branches.map((b) => ({ value: b.id, label: b.name })),
              ]}
            />

            <Input
              label="Date"
              type="date"
              value={filters.date}
              onChange={(e) => handleFilterChange('date', e.target.value)}
            />

            <Select
              label="Status"
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              options={[
                { value: '', label: 'All Statuses' },
                { value: ReservationStatus.PENDING, label: 'Pending' },
                { value: ReservationStatus.CONFIRMED, label: 'Confirmed' },
                { value: ReservationStatus.CANCELLED, label: 'Cancelled' },
                { value: ReservationStatus.COMPLETED, label: 'Completed' },
              ]}
            />

            <Input
              label="Phone Number"
              value={filters.phone_number}
              onChange={(e) => handleFilterChange('phone_number', e.target.value)}
              placeholder="Search by phone..."
            />
          </div>

          <div className="flex justify-end">
            <Button variant="outline" onClick={clearFilters}>
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingPage />
      ) : reservations.length === 0 ? (
        <EmptyState
          title="No reservations found"
          description="Try adjusting your filters to see more results"
        />
      ) : (
        <>
          <ReservationTable
            reservations={reservations}
            onStatusUpdate={handleStatusUpdate}
            onDelete={handleDelete}
          />

          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <div className="text-sm text-secondary-600">
                Page {page} of {totalPages}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
