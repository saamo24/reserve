'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getReservation, attachReservationToGuest } from '@/lib/api';
import type { ReservationResponse } from '@/lib/types';
import { formatDateDisplay, formatTime } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Navbar } from '@/components/Navbar';
import { LoadingPage } from '@/components/ui/loading';
import toast from 'react-hot-toast';

function ViewReservationContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const id = searchParams.get('id');
  const code = searchParams.get('code');

  const [reservation, setReservation] = useState<ReservationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchReservation() {
      if (!id || !code) {
        toast.error('Reservation ID and code are required');
        router.push('/my-reservations');
        return;
      }

      try {
        setIsLoading(true);
        const data = await getReservation(id, code);
        setReservation(data);
        try {
          await attachReservationToGuest(id, code);
          toast.success('Added to My Reservations');
        } catch {
          // Already attached or other; reservation still shown
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load reservation';
        toast.error(errorMessage);
        router.push('/my-reservations');
      } finally {
        setIsLoading(false);
      }
    }

    fetchReservation();
  }, [id, code, router]);

  if (isLoading) {
    return (
      <>
        <Navbar />
        <LoadingPage />
      </>
    );
  }

  if (!reservation) {
    return null;
  }

  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <Card variant="elevated">
            <CardHeader className="text-center">
              <CardTitle className="text-2xl">Your Reservation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-secondary-50 rounded-xl p-6 space-y-3">
                <div>
                  <p className="text-sm text-secondary-600">Name</p>
                  <p className="font-semibold text-secondary-900">{reservation.full_name}</p>
                </div>
                <div>
                  <p className="text-sm text-secondary-600">Phone</p>
                  <p className="font-semibold text-secondary-900">{reservation.phone_number}</p>
                </div>
                {reservation.email && (
                  <div>
                    <p className="text-sm text-secondary-600">Email</p>
                    <p className="font-semibold text-secondary-900">{reservation.email}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-secondary-600">Date & Time</p>
                  <p className="font-semibold text-secondary-900">
                    {formatDateDisplay(reservation.reservation_date)} at{' '}
                    {formatTime(reservation.start_time)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-secondary-600">Reservation ID</p>
                  <p className="font-semibold text-secondary-900 font-mono text-sm">
                    {reservation.id}
                  </p>
                </div>
                {reservation.notes && (
                  <div>
                    <p className="text-sm text-secondary-600">Special Requests</p>
                    <p className="font-semibold text-secondary-900">{reservation.notes}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm text-secondary-600">Status</p>
                  <span className="inline-block px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-medium">
                    {reservation.status}
                  </span>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 pt-4">
                <Link href="/my-reservations" className="flex-1">
                  <Button variant="outline" className="w-full">
                    Back to My Reservations
                  </Button>
                </Link>
                <Link href="/" className="flex-1">
                  <Button variant="primary" className="w-full">
                    Back to Home
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}

export default function ViewReservationPage() {
  return (
    <Suspense
      fallback={
        <>
          <Navbar />
          <LoadingPage />
        </>
      }
    >
      <ViewReservationContent />
    </Suspense>
  );
}
