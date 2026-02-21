'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getReservationsMe, devAttachReservationToGuest } from '@/lib/api';
import type { ReservationResponse } from '@/lib/types';
import { formatDateDisplay, formatTime } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Navbar } from '@/components/Navbar';
import { LoadingPage } from '@/components/ui/loading';

type RejectedError = Error & { status?: number };

export default function MyReservationsPage() {
  const router = useRouter();
  const [reservations, setReservations] = useState<ReservationResponse[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [viewId, setViewId] = useState('');
  const [viewCode, setViewCode] = useState('');
  const [viewError, setViewError] = useState<string | null>(null);
  const [devAttachId, setDevAttachId] = useState('');
  const [devAttachLoading, setDevAttachLoading] = useState(false);
  const [devAttachError, setDevAttachError] = useState<string | null>(null);

  const fetchReservations = React.useCallback(async () => {
    try {
      setError(null);
      setSessionExpired(false);
      const data = await getReservationsMe();
      setReservations(data);
    } catch (err) {
      const e = err as RejectedError;
      if (e.status === 401) {
        setSessionExpired(true);
        setReservations([]);
      } else {
        setError(e instanceof Error ? e.message : 'Something went wrong');
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        setIsLoading(true);
        await fetchReservations();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    run();
    return () => { cancelled = true; };
  }, [fetchReservations]);

  if (isLoading) {
    return (
      <>
        <Navbar />
        <LoadingPage />
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <Card variant="elevated">
            <CardHeader>
              <CardTitle className="text-2xl">My Reservations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {sessionExpired && (
                <>
                  <p className="text-secondary-700 text-center py-4">
                    Your session expired. You can refresh the page or view a reservation by code below.
                  </p>
                  <div className="border-t border-secondary-200 pt-6 mt-4">
                    <p className="text-sm font-medium text-secondary-700 mb-3">
                      View a reservation by code
                    </p>
                    <div className="space-y-3">
                      <Input
                        placeholder="Reservation ID"
                        value={viewId}
                        onChange={(e) => { setViewId(e.target.value); setViewError(null); }}
                        className="font-mono text-sm"
                      />
                      <Input
                        placeholder="Reservation code (8 characters)"
                        value={viewCode}
                        onChange={(e) => { setViewCode(e.target.value.trim()); setViewError(null); }}
                        className="font-mono"
                        maxLength={8}
                      />
                      {viewError && <p className="text-sm text-red-600">{viewError}</p>}
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => {
                          const id = viewId.trim();
                          const code = viewCode.trim();
                          if (!id || !code) { setViewError('Please enter both reservation ID and code.'); return; }
                          router.push(`/view-reservation?id=${encodeURIComponent(id)}&code=${encodeURIComponent(code)}`);
                        }}
                      >
                        View reservation
                      </Button>
                    </div>
                  </div>
                </>
              )}

              {error && !sessionExpired && (
                <p className="text-red-600 text-center py-4">{error}</p>
              )}

              {!sessionExpired && !error && reservations?.length === 0 && (
                <>
                  <p className="text-secondary-600 text-center py-4">
                    You have no reservations yet.
                  </p>
                  <div className="border-t border-secondary-200 pt-6 mt-4">
                    <p className="text-sm font-medium text-secondary-700 mb-3">
                      Have a confirmation code?
                    </p>
                    <p className="text-sm text-secondary-600 mb-4">
                      Enter your reservation ID and code (from your confirmation email or success page) to view a reservation.
                    </p>
                    <div className="space-y-3">
                      <Input
                        placeholder="Reservation ID (e.g. 73bc48c1-fe76-484f-...)"
                        value={viewId}
                        onChange={(e) => {
                          setViewId(e.target.value);
                          setViewError(null);
                        }}
                        className="font-mono text-sm"
                      />
                      <Input
                        placeholder="Reservation code (8 characters)"
                        value={viewCode}
                        onChange={(e) => {
                          setViewCode(e.target.value.trim());
                          setViewError(null);
                        }}
                        className="font-mono"
                        maxLength={8}
                      />
                      {viewError && (
                        <p className="text-sm text-red-600">{viewError}</p>
                      )}
                      <Button
                        variant="outline"
                        className="w-full"
                        onClick={() => {
                          const id = viewId.trim();
                          const code = viewCode.trim();
                          if (!id || !code) {
                            setViewError('Please enter both reservation ID and code.');
                            return;
                          }
                          if (code.length < 4) {
                            setViewError('Please enter your reservation code.');
                            return;
                          }
                          router.push(`/view-reservation?id=${encodeURIComponent(id)}&code=${encodeURIComponent(code)}`);
                        }}
                      >
                        View reservation
                      </Button>
                    </div>
                  </div>
                </>
              )}

              {!sessionExpired && !error && reservations && reservations.length > 0 && (
                <ul className="space-y-4">
                  {reservations.map((r) => (
                    <li key={r.id}>
                      <div className="bg-secondary-50 rounded-xl p-4 space-y-2">
                        <div className="flex justify-between items-start">
                          <p className="font-semibold text-secondary-900">{r.full_name}</p>
                          <span className="inline-block px-2 py-0.5 bg-secondary-200 text-secondary-800 rounded text-xs font-medium">
                            {r.status}
                          </span>
                        </div>
                        <p className="text-sm text-secondary-600">
                          {formatDateDisplay(r.reservation_date)} at {formatTime(r.start_time)}
                        </p>
                        <p className="text-sm text-secondary-600">{r.phone_number}</p>
                        {r.notes && (
                          <p className="text-sm text-secondary-500 italic">{r.notes}</p>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              {process.env.NODE_ENV === 'development' && (
                <div className="border-t border-amber-200 bg-amber-50/50 rounded-lg p-4 mt-4 space-y-2">
                  <p className="text-sm font-medium text-amber-800">Dev: link reservation to this session</p>
                  <p className="text-xs text-amber-700">
                    Paste a reservation ID (e.g. from admin or DB) to show it in My Reservations. Backend must have APP_ENV=development.
                  </p>
                  <div className="flex gap-2">
                    <Input
                      placeholder="Reservation ID (UUID)"
                      value={devAttachId}
                      onChange={(e) => { setDevAttachId(e.target.value); setDevAttachError(null); }}
                      className="font-mono text-sm flex-1"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={devAttachLoading || !devAttachId.trim()}
                      onClick={async () => {
                        const id = devAttachId.trim();
                        if (!id) return;
                        setDevAttachError(null);
                        setDevAttachLoading(true);
                        try {
                          await devAttachReservationToGuest(id);
                          await fetchReservations();
                          setDevAttachId('');
                        } catch (err) {
                          setDevAttachError(err instanceof Error ? err.message : 'Failed');
                        } finally {
                          setDevAttachLoading(false);
                        }
                      }}
                    >
                      {devAttachLoading ? 'Linking…' : 'Link'}
                    </Button>
                  </div>
                  {devAttachError && <p className="text-sm text-red-600">{devAttachError}</p>}
                </div>
              )}

              <div className="pt-4">
                <Link href="/">
                  <Button variant="outline" className="w-full">
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
