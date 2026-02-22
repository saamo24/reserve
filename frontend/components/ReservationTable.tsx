'use client';

import React, { useState } from 'react';
import { ReservationResponse, ReservationStatus } from '@/lib/types';
import { formatDateDisplay, formatTime } from '@/lib/utils';
import { Select } from './ui/select';
import { Button } from './ui/button';
import toast from 'react-hot-toast';

interface ReservationTableProps {
  reservations: ReservationResponse[];
  onStatusUpdate: (id: string, status: ReservationStatus) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onViewDetails?: (reservation: ReservationResponse) => void;
  isLoading?: boolean;
}

export function ReservationTable({
  reservations,
  onStatusUpdate,
  onDelete,
  onViewDetails,
  isLoading = false,
}: ReservationTableProps) {
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const statusOptions = [
    { value: ReservationStatus.PENDING, label: 'Pending' },
    { value: ReservationStatus.CONFIRMED, label: 'Confirmed' },
    { value: ReservationStatus.CANCELLED, label: 'Cancelled' },
    { value: ReservationStatus.COMPLETED, label: 'Completed' },
  ];

  const handleStatusChange = async (id: string, newStatus: ReservationStatus) => {
    try {
      setUpdatingId(id);
      await onStatusUpdate(id, newStatus);
      toast.success('Reservation status updated');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update status';
      toast.error(errorMessage);
    } finally {
      setUpdatingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this reservation?')) {
      return;
    }

    try {
      setDeletingId(id);
      await onDelete(id);
      toast.success('Reservation deleted');
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete reservation';
      toast.error(errorMessage);
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusColor = (status: ReservationStatus) => {
    switch (status) {
      case ReservationStatus.CONFIRMED:
        return 'bg-green-100 text-green-700';
      case ReservationStatus.PENDING:
        return 'bg-yellow-100 text-yellow-700';
      case ReservationStatus.CANCELLED:
        return 'bg-red-100 text-red-700';
      case ReservationStatus.COMPLETED:
        return 'bg-blue-100 text-blue-700';
      default:
        return 'bg-secondary-100 text-secondary-700';
    }
  };

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
      </div>
    );
  }

  if (reservations.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-secondary-600">No reservations found</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-secondary-200 bg-white rounded-xl overflow-hidden">
        <thead className="bg-secondary-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Name
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Phone
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Email
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Date & Time
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-secondary-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-secondary-200">
          {reservations.map((reservation) => (
            <tr key={reservation.id} className="hover:bg-secondary-50 transition-colors">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-secondary-900">{reservation.full_name}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-secondary-600">{reservation.phone_number}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-secondary-600">{reservation.email || '-'}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-secondary-900">
                  {formatDateDisplay(reservation.reservation_date)}
                </div>
                <div className="text-xs text-secondary-500">
                  {formatTime(reservation.start_time)} - {formatTime(reservation.end_time)}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <Select
                  value={reservation.status}
                  onChange={(e) =>
                    handleStatusChange(reservation.id, e.target.value as ReservationStatus)
                  }
                  options={statusOptions}
                  className="w-32"
                  disabled={updatingId === reservation.id}
                />
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div className="flex items-center justify-end gap-2">
                  {onViewDetails && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onViewDetails(reservation)}
                    >
                      View
                    </Button>
                  )}
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => handleDelete(reservation.id)}
                    isLoading={deletingId === reservation.id}
                  >
                    Delete
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
