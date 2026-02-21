'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { createReservation, getSlots } from '@/lib/api';
import { BranchResponse, Slot, TableResponse } from '@/lib/types';
import { getTodayDate, formatDate, isPastDate } from '@/lib/utils';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import toast from 'react-hot-toast';

const createReservationSchema = (tableCapacity: number) => z.object({
  full_name: z.preprocess(
    (val: unknown) => {
      if (val === null || val === undefined) return '';
      if (typeof val === 'string') return val.trim();
      return String(val);
    },
    z.string().min(1, 'Full name is required').max(255, 'Name is too long')
  ),
  phone_number: z.preprocess(
    (val: unknown) => {
      if (val === null || val === undefined) return '';
      if (typeof val === 'string') return val.trim();
      return String(val);
    },
    z
      .string()
      .min(1, 'Phone number is required')
      .regex(/^[\d\s\-\+\(\)]+$/, 'Invalid phone number format')
  ),
  email: z.preprocess(
    (val: unknown) => {
      if (val === '' || val === null || val === undefined) return '';
      if (typeof val === 'string') return val.trim();
      return '';
    },
    z.union([
      z.string().email('Invalid email address'),
      z.literal(''),
    ])
  ),
  number_of_guests: z.preprocess(
    (val: unknown) => {
      // Handle empty, null, undefined
      if (val === '' || val === null || val === undefined) {
        return undefined;
      }
      // Handle number (in case it comes as number somehow)
      if (typeof val === 'number') {
        // NaN or invalid numbers become undefined
        if (isNaN(val) || !isFinite(val)) {
          return undefined;
        }
        return val;
      }
      // Handle string (most common case from HTML input)
      if (typeof val === 'string') {
        const trimmed = val.trim();
        if (trimmed === '') return undefined;
        const num = Number(trimmed);
        // Check if conversion was successful
        if (isNaN(num) || !isFinite(num)) return undefined;
        // Ensure it's an integer
        const intNum = Math.floor(num);
        return intNum;
      }
      return undefined;
    },
    z
      .number({
        required_error: 'Number of guests is required',
        invalid_type_error: 'Please enter a valid number',
      })
      .int('Number of guests must be a whole number')
      .min(1, 'At least 1 guest required')
      .max(tableCapacity, `This table can only accommodate ${tableCapacity} guests`)
  ),
  reservation_date: z.preprocess(
    (val: unknown) => {
      if (val === null || val === undefined) return '';
      return String(val);
    },
    z.string({ required_error: 'Date is required' }).min(1, 'Date is required')
  ),
  start_time: z.preprocess(
    (val: unknown) => {
      if (val === null || val === undefined) return '';
      return String(val);
    },
    z.string({ required_error: 'Time is required' }).min(1, 'Time is required')
  ),
  notes: z.preprocess(
    (val: unknown) => {
      if (val === '' || val === null || val === undefined) {
        return undefined;
      }
      if (typeof val === 'string') {
        const trimmed = val.trim();
        return trimmed === '' ? undefined : trimmed;
      }
      return undefined;
    },
    z.string().max(1000, 'Notes are too long').optional()
  ),
});

type ReservationFormData = z.infer<ReturnType<typeof createReservationSchema>>;

interface ReservationFormProps {
  branch: BranchResponse;
  table: TableResponse;
  onBack?: () => void;
}

export function ReservationForm({ branch, table, onBack }: ReservationFormProps) {
  const router = useRouter();
  const [availableSlots, setAvailableSlots] = useState<Slot[]>([]);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const executionRef = useRef(0);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitted },
    setValue,
    getValues,
  } = useForm<ReservationFormData>({
    resolver: zodResolver(createReservationSchema(table.capacity)),
    mode: 'onSubmit',
    reValidateMode: 'onChange',
    shouldUnregister: false,
    defaultValues: {
      full_name: '',
      phone_number: '',
      email: '',
      number_of_guests: Math.min(2, table.capacity),
      reservation_date: getTodayDate(),
      start_time: '',
      notes: '',
    },
  });

  const selectedDate = watch('reservation_date');

  // Debug: Log validation failures
  useEffect(() => {
    if (isSubmitted && Object.keys(errors).length > 0) {
      const values = getValues();
      console.log('❌ Validation failed!');
      console.log('Form values:', values);
      console.log('Validation errors:', errors);
      console.log('Full name value:', values.full_name, 'Type:', typeof values.full_name);
      console.log('Phone value:', values.phone_number, 'Type:', typeof values.phone_number);
      console.log('Number of guests value:', values.number_of_guests, 'Type:', typeof values.number_of_guests);
      console.log('Date value:', values.reservation_date, 'Type:', typeof values.reservation_date);
      console.log('Time value:', values.start_time, 'Type:', typeof values.start_time);
    }
  }, [isSubmitted, errors, getValues]);

  // Fetch slots when date changes or on mount
  useEffect(() => {
    const executionId = ++executionRef.current;
    let isCancelled = false;

    async function fetchSlots() {
      if (!selectedDate) {
        setValue('start_time', '');
        return;
      }

      // Ensure we have a valid branch ID
      if (!branch?.id) {
        return;
      }

      // HTML date input already returns YYYY-MM-DD format, but ensure it's correct
      let formattedDate = selectedDate;
      if (!formattedDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
        formattedDate = formatDate(selectedDate);
      }
      
      // Validate date format
      if (!formattedDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return;
      }
      
      if (isPastDate(formattedDate)) {
        return;
      }

      let loadingSetToFalse = false;
      
      try {
        setIsLoadingSlots(true);
        const slots = await getSlots(branch.id, formattedDate);
        
        // Check if this execution is still current
        if (executionId === executionRef.current && !isCancelled) {
          // API returns a plain array of slots: [{start_time: "HH:MM", end_time: "HH:MM"}, ...]
          const slotsArray = Array.isArray(slots) ? slots : [];
          
          // Set slots and loading state together
          setAvailableSlots(slotsArray);
          setIsLoadingSlots(false);
          loadingSetToFalse = true;
          
          // Reset time selection if current selection is not available
          const currentTime = watch('start_time');
          if (currentTime && slotsArray.length > 0) {
            // Normalize time format for comparison (remove seconds if present)
            const normalizedCurrent = currentTime.includes(':') 
              ? currentTime.split(':').slice(0, 2).join(':')
              : currentTime;
            const isAvailable = slotsArray.some((s: Slot) => {
              const normalizedSlot = s.start_time.includes(':')
                ? s.start_time.split(':').slice(0, 2).join(':')
                : s.start_time;
              return normalizedSlot === normalizedCurrent;
            });
            if (!isAvailable) {
              setValue('start_time', '');
            }
          } else if (currentTime && slotsArray.length === 0) {
            setValue('start_time', '');
          }
        }
      } catch (err) {
        // Check if this execution is still current
        if (executionId === executionRef.current && !isCancelled) {
          const errorMessage = err instanceof Error ? err.message : 'Failed to load available times';
          console.error('Error fetching slots:', err);
          
          // Only clear slots on error if it's a real error (not just empty response)
          if (err && typeof err === 'object' && 'response' in err) {
            const apiError = err as any;
            // If it's a 404 or 500, clear slots. If it's 200 with empty array, that's OK
            if (apiError.response?.status !== 200) {
              setAvailableSlots([]);
              setValue('start_time', '');
            }
          } else {
            setAvailableSlots([]);
            setValue('start_time', '');
          }
        }
      } finally {
        // Only set loading to false if we haven't already set it in the success case
        if (executionId === executionRef.current && !isCancelled && !loadingSetToFalse) {
          setIsLoadingSlots(false);
        }
      }
    }

    fetchSlots();

    return () => {
      isCancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, branch?.id]);

  const onSubmit = async (data: ReservationFormData) => {
    try {
      setIsSubmitting(true);

      // Debug: Log the validated data
      console.log('Form data submitted:', data);

      // Ensure date is in YYYY-MM-DD format
      let formattedDate = formatDate(data.reservation_date);
      // If formatDate didn't work, try direct format
      if (!formattedDate.match(/^\d{4}-\d{2}-\d{2}$/)) {
        const dateObj = new Date(data.reservation_date);
        formattedDate = dateObj.toISOString().split('T')[0];
      }

      // Ensure time is in HH:mm format (remove seconds if present)
      let formattedTime = data.start_time;
      if (formattedTime.includes(':')) {
        const parts = formattedTime.split(':');
        if (parts.length >= 2) {
          formattedTime = `${parts[0].padStart(2, '0')}:${parts[1].padStart(2, '0')}`;
        }
      }

      const reservationData = {
        branch_id: branch.id,
        table_id: table.id,
        reservation_date: formattedDate,
        start_time: formattedTime,
        full_name: data.full_name,
        phone_number: data.phone_number,
        email: data.email && data.email !== '' ? data.email : null,
        notes: data.notes || null,
      };

      const reservation = await createReservation(reservationData);
      toast.success('Reservation created successfully!');
      
      // Get restaurant slug from branch name
      const slug = branch.name
        .toLowerCase()
        .trim()
        .replace(/[^\w\s-]/g, '')
        .replace(/[\s_-]+/g, '-')
        .replace(/^-+|-+$/g, '');
      const codeParam = reservation.reservation_code ? `&code=${encodeURIComponent(reservation.reservation_code)}` : '';
      router.push(`/${encodeURIComponent(slug)}/success?id=${reservation.id}${codeParam}`);
    } catch (err: any) {
      const errorMessage =
        err?.response?.data?.detail || err?.message || 'Failed to create reservation';
      toast.error(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Get minimum date (today)
  const minDate = getTodayDate();

  return (
    <Card variant="elevated">
      <CardHeader>
        <CardTitle>Make a Reservation</CardTitle>
        <div className="mt-2 p-3 bg-secondary-50 rounded-lg">
          <p className="text-sm text-secondary-600">
            <span className="font-medium">Selected Table:</span> Table {table.table_number} ({table.capacity} guests, {table.location})
          </p>
        </div>
      </CardHeader>
      <CardContent>
        <form 
          onSubmit={handleSubmit(
            onSubmit,
            (errors) => {
              // This runs when validation fails
              console.log('🚫 Form validation failed:', errors);
              console.log('Current form values:', getValues());
            }
          )} 
          className="space-y-6"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Input
              label="Full Name"
              {...register('full_name')}
              error={isSubmitted ? errors.full_name?.message : undefined}
              placeholder="John Doe"
              required
            />

            <Input
              label="Phone Number"
              {...register('phone_number')}
              error={isSubmitted ? errors.phone_number?.message : undefined}
              placeholder="+1 (555) 123-4567"
              required
            />

            <Input
              label="Email (Optional)"
              type="email"
              {...register('email')}
              error={isSubmitted ? errors.email?.message : undefined}
              placeholder="john@example.com"
            />

            <Input
              label={`Number of Guests (max ${table.capacity})`}
              type="number"
              {...register('number_of_guests')}
              error={isSubmitted ? errors.number_of_guests?.message : undefined}
              min={1}
              max={table.capacity}
              required
            />

            <Input
              label="Date"
              type="date"
              {...register('reservation_date')}
              error={isSubmitted ? errors.reservation_date?.message : undefined}
              min={minDate}
              required
            />

            <div className="w-full">
              <Select
                label="Time"
                {...register('start_time')}
                error={isSubmitted ? errors.start_time?.message : undefined}
                options={
                  isLoadingSlots
                    ? [{ value: '', label: 'Loading available times...', disabled: true }]
                    : availableSlots.length === 0
                      ? [{ value: '', label: 'No available times for this date', disabled: true }]
                      : [
                          { value: '', label: '-- Select a time --' },
                          ...availableSlots.map((slot: Slot) => ({
                            value: slot.start_time,
                            label: slot.start_time,
                          }))
                        ]
                }
                disabled={isLoadingSlots}
                required
              />
              {!isLoadingSlots && availableSlots.length === 0 && selectedDate && (
                <p className="mt-1 text-sm text-secondary-500">
                  Please select a different date or contact the restaurant directly.
                </p>
              )}
            </div>
          </div>

          <Input
            label="Special Requests (Optional)"
            {...register('notes')}
            error={isSubmitted ? errors.notes?.message : undefined}
            placeholder="Any special requests or dietary requirements..."
            className="w-full"
          />

          <div className="flex justify-between gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={onBack || (() => router.push('/'))}
              disabled={isSubmitting}
            >
              {onBack ? 'Back to Tables' : 'Cancel'}
            </Button>
            <Button type="submit" variant="primary" isLoading={isSubmitting}>
              Book Reservation
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
