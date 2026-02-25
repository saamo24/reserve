'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getAdminReservation } from '@/lib/api';
import { ReservationResponse } from '@/lib/types';
import { formatDateDisplay, formatTime } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LoadingPage } from '@/components/ui/loading';
import toast from 'react-hot-toast';

function ReservationDetailContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const reservationId = params.id as string;
  const code = searchParams.get('code');

  const [reservation, setReservation] = useState<ReservationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchReservation() {
      if (!reservationId) {
        toast.error('Reservation ID not found');
        router.push('/admin/reservations');
        return;
      }

      try {
        setIsLoading(true);
        const data = await getAdminReservation(reservationId, code || undefined);
        setReservation(data);
      } catch (err: any) {
        const errorMessage =
          err?.response?.data?.detail || err?.message || 'Failed to load reservation';
        toast.error(errorMessage);
        router.push('/admin/reservations');
      } finally {
        setIsLoading(false);
      }
    }

    fetchReservation();
  }, [reservationId, code, router]);

  if (isLoading) {
    return <LoadingPage />;
  }

  if (!reservation) {
    return null;
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-secondary-900">Reservation Details</h1>
        <p className="text-secondary-600 mt-2">View full reservation information</p>
      </div>

      <Card variant="elevated">
        <CardHeader>
          <CardTitle>Reservation Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-secondary-600 mb-1">Name</p>
              <p className="font-semibold text-secondary-900">{reservation.full_name}</p>
            </div>

            <div>
              <p className="text-sm text-secondary-600 mb-1">Phone Number</p>
              <p className="font-semibold text-secondary-900">{reservation.phone_number}</p>
            </div>

            {reservation.email && (
              <div>
                <p className="text-sm text-secondary-600 mb-1">Email</p>
                <p className="font-semibold text-secondary-900">{reservation.email}</p>
              </div>
            )}

            <div>
              <p className="text-sm text-secondary-600 mb-1">Reservation Date</p>
              <p className="font-semibold text-secondary-900">
                {formatDateDisplay(reservation.reservation_date)}
              </p>
            </div>

            <div>
              <p className="text-sm text-secondary-600 mb-1">Start Time</p>
              <p className="font-semibold text-secondary-900">
                {formatTime(reservation.start_time)}
              </p>
            </div>

            <div>
              <p className="text-sm text-secondary-600 mb-1">End Time</p>
              <p className="font-semibold text-secondary-900">{formatTime(reservation.end_time)}</p>
            </div>

            <div>
              <p className="text-sm text-secondary-600 mb-1">Status</p>
              <span className="inline-block px-3 py-1 bg-secondary-200 text-secondary-800 rounded-full text-sm font-medium">
                {reservation.status}
              </span>
            </div>

            {reservation.reservation_code && (
              <div>
                <p className="text-sm text-secondary-600 mb-1">Reservation Code</p>
                <p className="font-semibold text-secondary-900 font-mono text-sm">
                  {reservation.reservation_code}
                </p>
              </div>
            )}

            <div>
              <p className="text-sm text-secondary-600 mb-1">Reservation ID</p>
              <p className="font-semibold text-secondary-900 font-mono text-xs break-all">
                {reservation.id}
              </p>
            </div>

            <div>
              <p className="text-sm text-secondary-600 mb-1">Branch ID</p>
              <p className="font-semibold text-secondary-900 font-mono text-xs break-all">
                {reservation.branch_id}
              </p>
            </div>

            <div>
              <p className="text-sm text-secondary-600 mb-1">Table ID</p>
              <p className="font-semibold text-secondary-900 font-mono text-xs break-all">
                {reservation.table_id}
              </p>
            </div>
          </div>

          {reservation.notes && (
            <div className="border-t border-secondary-200 pt-4">
              <p className="text-sm text-secondary-600 mb-2">Special Requests / Notes</p>
              <p className="text-secondary-900 bg-secondary-50 rounded-lg p-3">
                {reservation.notes}
              </p>
            </div>
          )}

          {reservation.qr_code && (
            <div className="border-t border-secondary-200 pt-4">
              <p className="text-sm text-secondary-600 mb-3 text-center">
                QR Code (scan to view this reservation)
              </p>
              <div className="flex justify-center">
                <div className="bg-white rounded-xl p-4 border border-secondary-200">
                  <img
                    src={`data:image/png;base64,${reservation.qr_code}`}
                    alt="Reservation QR code"
                    className="w-48 h-48 object-contain"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="border-t border-secondary-200 pt-4 flex gap-4">
            <Link href="/admin/reservations" className="flex-1">
              <Button variant="outline" className="w-full">
                Back to Reservations
              </Button>
            </Link>
            <Link href={`/admin/reservations?reservation_id=${reservation.id}`} className="flex-1">
              <Button variant="primary" className="w-full">
                Edit Reservation
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AdminReservationDetailPage() {
  return (
    <Suspense
      fallback={
        <div>
          <LoadingPage />
        </div>
      }
    >
      <ReservationDetailContent />
    </Suspense>
  );
}
