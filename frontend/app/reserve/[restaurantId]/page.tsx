'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { getBranches, getBranch, getSlots, getLayoutPublic } from '@/lib/api';
import type { BranchResponse, LayoutTable, Slot, TableResponse } from '@/lib/types';
import { createSlugToBranchMap, getBranchIdFromSlug, getTodayDate } from '@/lib/utils';
import { layoutHasTables } from '@/lib/types';
import { Navbar } from '@/components/Navbar';
import { ReservationForm } from '@/components/ReservationForm';
import { TableSelection } from '@/components/TableSelection';
import { LoadingPage } from '@/components/ui/loading';

const UserLayoutViewer = dynamic(
  () =>
    import('@/components/layout/UserLayoutViewer').then((m) => ({
      default: m.UserLayoutViewer,
    })),
  { ssr: false }
);
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import toast from 'react-hot-toast';

function isUuid(s: string): boolean {
  const u =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return u.test(s);
}

function layoutTableToTableResponse(
  t: LayoutTable,
  branchId: string
): TableResponse {
  return {
    id: t.id,
    branch_id: branchId,
    table_number: t.table_number,
    capacity: t.capacity,
    location: 'INDOOR',
    is_active: true,
    created_at: '',
    updated_at: '',
  };
}

export default function ReservePage() {
  const params = useParams();
  const router = useRouter();
  const restaurantId = (params?.restaurantId as string) ?? '';

  const [branch, setBranch] = useState<BranchResponse | null>(null);
  const [slugMap, setSlugMap] = useState<Map<string, BranchResponse>>(new Map());
  const [isLoading, setIsLoading] = useState(true);
  const [date, setDate] = useState(getTodayDate());
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [selectedTableId, setSelectedTableId] = useState<string | null>(null);
  const [selectedLayoutTable, setSelectedLayoutTable] = useState<LayoutTable | null>(null);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [selectedFloorId, setSelectedFloorId] = useState<string | null>(null);
  const [confirmedTable, setConfirmedTable] = useState(false);
  const [hasLayout, setHasLayout] = useState(false);
  const [containerSize, setContainerSize] = useState({ width: 600, height: 400 });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function run() {
      if (!restaurantId) return;
      try {
        setIsLoading(true);
        const branches = await getBranches();
        const map = createSlugToBranchMap(branches);
        setSlugMap(map);
        const branchId = isUuid(restaurantId)
          ? restaurantId
          : getBranchIdFromSlug(restaurantId, map);
        if (!branchId) {
          toast.error('Restaurant not found');
          router.push('/');
          return;
        }
        const branchData = await getBranch(branchId);
        if (!branchData.is_active) {
          toast.error('This restaurant is currently closed');
          router.push('/');
          return;
        }
        setBranch(branchData);
        try {
          const layout = await getLayoutPublic(branchId);
          setHasLayout(layoutHasTables(layout));
        } catch {
          setHasLayout(false);
        }
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'Failed to load');
        router.push('/');
      } finally {
        setIsLoading(false);
      }
    }
    run();
  }, [restaurantId, router]);

  useEffect(() => {
    if (!branch) return;
    getSlots(branch.id, date)
      .then(setSlots)
      .catch(() => setSlots([]));
    setSelectedSlot(null);
    setSelectedTableId(null);
    setSelectedLayoutTable(null);
    setSelectedZoneId(null);
    setSelectedFloorId(null);
    setConfirmedTable(false);
  }, [branch, date]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setContainerSize({ width: el.offsetWidth || 600, height: el.offsetHeight || 400 });
    });
    ro.observe(el);
    setContainerSize({ width: el.offsetWidth || 600, height: el.offsetHeight || 400 });
    return () => ro.disconnect();
  }, [hasLayout]);

  const handleSelectTable = (
    id: string | null,
    table: LayoutTable | null,
    zoneId: string | null,
    floorId: string | null
  ) => {
    setSelectedTableId(id);
    setSelectedLayoutTable(table);
    setSelectedZoneId(zoneId);
    setSelectedFloorId(floorId);
  };

  const handleContinueWithTable = () => {
    if (!branch || !selectedLayoutTable || !selectedSlot) return;
    setConfirmedTable(true);
  };

  const tableForForm: TableResponse | null =
    branch && selectedLayoutTable
      ? layoutTableToTableResponse(selectedLayoutTable, branch.id)
      : null;

  const showForm =
    Boolean(tableForForm && selectedSlot && (!hasLayout || confirmedTable));

  if (isLoading) {
    return (
      <>
        <Navbar />
        <LoadingPage />
      </>
    );
  }

  if (!branch) return null;

  if (showForm && tableForForm) {
    return (
      <>
        <Navbar />
        <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <ReservationForm
              branch={branch}
              table={tableForForm}
              initialDate={date}
              initialTime={selectedSlot?.start_time}
              onBack={() => {
                setSelectedTableId(null);
                setSelectedLayoutTable(null);
                setSelectedZoneId(null);
                setSelectedFloorId(null);
                setConfirmedTable(false);
              }}
            />
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <Card variant="elevated" className="mb-8">
            <CardContent className="p-6">
              <h1 className="text-3xl font-bold text-secondary-900 mb-2">{branch.name}</h1>
              <p className="text-secondary-600 mb-4">{branch.address}</p>
            </CardContent>
          </Card>

          <Card className="mb-6">
            <CardContent className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Date</label>
                <Input
                  type="date"
                  value={date}
                  min={getTodayDate()}
                  onChange={(e) => setDate(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Time</label>
                <select
                  value={selectedSlot ? `${selectedSlot.start_time}-${selectedSlot.end_time}` : ''}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (!v) {
                      setSelectedSlot(null);
                      return;
                    }
                    const [start_time, end_time] = v.split('-');
                    setSelectedSlot({ start_time, end_time });
                  }}
                  className="w-full rounded-lg border border-secondary-300 px-3 py-2 text-sm"
                >
                  <option value="">Select time</option>
                  {slots.map((s) => (
                    <option
                      key={`${s.start_time}-${s.end_time}`}
                      value={`${s.start_time}-${s.end_time}`}
                    >
                      {s.start_time.slice(0, 5)} – {s.end_time.slice(0, 5)}
                    </option>
                  ))}
                </select>
              </div>
            </CardContent>
          </Card>

          {!selectedSlot ? (
            <p className="text-secondary-600">Select date and time to choose a table.</p>
          ) : hasLayout ? (
            <div ref={containerRef} className="min-h-[400px]">
              <UserLayoutViewer
                branchId={branch.id}
                date={date}
                startTime={selectedSlot.start_time}
                endTime={selectedSlot.end_time}
                selectedTableId={selectedTableId}
                onSelectTable={handleSelectTable}
                containerWidth={containerSize.width}
                containerHeight={containerSize.height}
              />
              <div className="mt-4 flex justify-end">
                <Button
                  variant="primary"
                  onClick={handleContinueWithTable}
                  disabled={!selectedTableId}
                >
                  Continue with selected table
                </Button>
              </div>
            </div>
          ) : (
            <TableSelection
              branch={branch}
              onTableSelect={(table) => {
                setSelectedLayoutTable({
                  id: table.id,
                  x: 0,
                  y: 0,
                  width: 80,
                  height: 60,
                  rotation: 0,
                  shape: 'rect',
                  capacity: table.capacity,
                  table_number: table.table_number,
                });
                setSelectedTableId(table.id);
              }}
            />
          )}
        </div>
      </div>
    </>
  );
}
