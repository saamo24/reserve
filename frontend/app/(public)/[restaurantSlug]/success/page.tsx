'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams, useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getReservation, attachReservationToGuest, getGuestMe } from '@/lib/api';
import { ReservationResponse } from '@/lib/types';
import { formatDateDisplay, formatTime } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Navbar } from '@/components/Navbar';
import { LoadingPage } from '@/components/ui/loading';
import toast from 'react-hot-toast';

export default function SuccessPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const restaurantSlug = params.restaurantSlug as string;
  const reservationId = searchParams.get('id');
  const code = searchParams.get('code');

  const [reservation, setReservation] = useState<ReservationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showTelegramPopup, setShowTelegramPopup] = useState(false);
  const [tgBotUsername, setTgBotUsername] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReservation() {
      if (!reservationId) {
        toast.error('Reservation ID not found');
        router.push('/');
        return;
      }

      try {
        setIsLoading(true);
        const data = await getReservation(reservationId, code ?? undefined);
        setReservation(data);
        if (code) {
          try {
            await attachReservationToGuest(reservationId, code);
          } catch {
            // Already attached or other
          }
        }
        try {
          const guestMe = await getGuestMe();
          setTgBotUsername(guestMe.tg_bot_username);
          if (
            !guestMe.telegram_linked &&
            guestMe.tg_bot_username &&
            data.reservation_code
          ) {
            setShowTelegramPopup(true);
          }
        } catch {
          // Guest me optional; ignore
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load reservation';
        toast.error(errorMessage);
        router.push('/');
      } finally {
        setIsLoading(false);
      }
    }

    fetchReservation();
  }, [reservationId, code, router]);

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

  const telegramBotLink =
    tgBotUsername && reservation?.reservation_code
      ? `https://t.me/${tgBotUsername}?start=${reservation.reservation_code}`
      : null;

  return (
    <>
      <Navbar />
      {showTelegramPopup && telegramBotLink && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="telegram-popup-title"
        >
          <Card variant="elevated" className="w-full max-w-md">
            <CardHeader className="text-center">
              <CardTitle id="telegram-popup-title" className="text-lg">
                Get reservation updates in Telegram
              </CardTitle>
              <p className="text-sm text-secondary-600 mt-1">
                Open the bot to link your account and receive confirmations and reminders.
              </p>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Button
                variant="primary"
                className="w-full"
                onClick={() => window.open(telegramBotLink, '_blank', 'noopener,noreferrer')}
              >
                Open Telegram
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => setShowTelegramPopup(false)}
              >
                Maybe later
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
        <div className="max-w-2xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-6 sm:py-8 md:py-12">
          <Card variant="elevated">
            <CardHeader className="text-center px-4 sm:px-6">
              <div className="mx-auto w-12 h-12 sm:w-16 sm:h-16 bg-green-100 rounded-full flex items-center justify-center mb-3 sm:mb-4">
                <svg
                  className="w-6 h-6 sm:w-8 sm:h-8 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <CardTitle className="text-xl sm:text-2xl">Reservation Confirmed!</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 px-4 sm:px-6 pb-4 sm:pb-6">
              <div className="bg-secondary-50 rounded-xl p-4 sm:p-6 space-y-3">
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
                    {formatDateDisplay(reservation.reservation_date)} at {formatTime(reservation.start_time)}
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

              {reservation.qr_code && (
                <div className="border-t border-secondary-200 pt-4">
                  <div className="flex flex-col items-center gap-3">
                    <p className="text-sm font-medium text-secondary-900">QR Code</p>
                    <p className="text-xs text-secondary-600 text-center">
                      Scan this code to view your reservation details
                    </p>
                    <div className="bg-white rounded-xl p-4 border-2 border-secondary-200 shadow-sm">
                      <img
                        src={`data:image/png;base64,${reservation.qr_code}`}
                        alt="Reservation QR code"
                        className="w-48 h-48 object-contain"
                      />
                    </div>
                  </div>
                </div>
              )}

              <div className="flex flex-col gap-3 sm:gap-4 pt-4">
                <Link href={`/${restaurantSlug}`} className="w-full">
                  <Button variant="outline" className="w-full">
                    Make Another Reservation
                  </Button>
                </Link>
                <Link href="/my-reservations" className="w-full">
                  <Button variant="outline" className="w-full">
                    View my reservations
                  </Button>
                </Link>
                <Link href="/" className="w-full">
                  <Button variant="primary" className="w-full">
                    Back to Home
                  </Button>
                </Link>
              </div>

              <p className="text-xs sm:text-sm text-secondary-500 text-center pt-4">
                A confirmation email has been sent to {reservation.email || 'your email address'}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
