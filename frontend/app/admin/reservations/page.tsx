'use client';

import React, { useEffect, useState } from 'react';
import { listReservations, updateReservation, listBranches, getAdminReservation } from '@/lib/api';
import { ReservationResponse, ReservationStatus, BranchResponse } from '@/lib/types';
import { formatDateDisplay, formatTime } from '@/lib/utils';
import { ReservationTable } from '@/components/ReservationTable';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
  const [detailReservation, setDetailReservation] = useState<ReservationResponse | null>(null);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
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

  const handleViewDetails = async (reservation: ReservationResponse) => {
    try {
      setIsLoadingDetails(true);
      // Fetch full reservation details to ensure we have the QR code
      const fullReservation = await getAdminReservation(reservation.id);
      setDetailReservation(fullReservation);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load reservation details';
      toast.error(errorMessage);
      // Fallback to showing the reservation from the list if fetch fails
      setDetailReservation(reservation);
    } finally {
      setIsLoadingDetails(false);
    }
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
            onViewDetails={handleViewDetails}
          />

          {detailReservation && (
            <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
              <Card variant="elevated" className="w-full max-w-lg max-h-[90vh] overflow-y-auto">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle>Reservation details</CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setDetailReservation(null)}
                    aria-label="Close"
                  >
                    Close
                  </Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  {isLoadingDetails ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                    </div>
                  ) : (
                    <>
                      <div className="grid grid-cols-1 gap-3 text-sm">
                        <div>
                          <p className="text-secondary-600">Name</p>
                          <p className="font-semibold text-secondary-900">{detailReservation.full_name}</p>
                        </div>
                        <div>
                          <p className="text-secondary-600">Phone</p>
                          <p className="font-semibold text-secondary-900">{detailReservation.phone_number}</p>
                        </div>
                        {detailReservation.email && (
                          <div>
                            <p className="text-secondary-600">Email</p>
                            <p className="font-semibold text-secondary-900">{detailReservation.email}</p>
                          </div>
                        )}
                        <div>
                          <p className="text-secondary-600">Date & time</p>
                          <p className="font-semibold text-secondary-900">
                            {formatDateDisplay(detailReservation.reservation_date)} at{' '}
                            {formatTime(detailReservation.start_time)}
                          </p>
                        </div>
                        <div>
                          <p className="text-secondary-600">Status</p>
                          <span className="inline-block px-2 py-0.5 bg-secondary-200 text-secondary-800 rounded text-xs font-medium">
                            {detailReservation.status}
                          </span>
                        </div>
                        {detailReservation.notes && (
                          <div>
                            <p className="text-secondary-600">Notes</p>
                            <p className="font-semibold text-secondary-900">{detailReservation.notes}</p>
                          </div>
                        )}
                      </div>
                      {detailReservation.qr_code ? (
                        <div className="border-t border-secondary-200 pt-4 flex flex-col items-center gap-3">
                          <p className="text-sm font-medium text-secondary-900">QR Code</p>
                          <p className="text-xs text-secondary-600 text-center">
                            Scan this code to view reservation details
                          </p>
                          <div className="bg-white rounded-xl p-4 border-2 border-secondary-200 shadow-sm">
                            <img
                              src={`data:image/png;base64,${detailReservation.qr_code}`}
                              alt="Reservation QR code"
                              className="w-48 h-48 object-contain"
                            />
                          </div>
                        </div>
                      ) : (
                        <div className="border-t border-secondary-200 pt-4">
                          <p className="text-sm text-secondary-500 text-center italic">
                            QR code not available for this reservation
                          </p>
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

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
