'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { getBranches, getBranch } from '@/lib/api';
import { BranchResponse, TableResponse } from '@/lib/types';
import { createSlugToBranchMap, getBranchIdFromSlug } from '@/lib/utils';
import { Navbar } from '@/components/Navbar';
import { ReservationForm } from '@/components/ReservationForm';
import { TableSelection } from '@/components/TableSelection';
import { LoadingPage } from '@/components/ui/loading';
import { Card, CardContent } from '@/components/ui/card';
import toast from 'react-hot-toast';

export default function ReservationPage() {
  const params = useParams();
  const router = useRouter();
  const restaurantSlug = params.restaurantSlug as string;

  const [branch, setBranch] = useState<BranchResponse | null>(null);
  const [selectedTable, setSelectedTable] = useState<TableResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [slugMap, setSlugMap] = useState<Map<string, BranchResponse>>(new Map());

  useEffect(() => {
    async function fetchBranchData() {
      try {
        setIsLoading(true);
        // Fetch all branches to create slug map
        const branches = await getBranches();
        const map = createSlugToBranchMap(branches);
        setSlugMap(map);

        // Get branch ID from slug
        const branchId = getBranchIdFromSlug(restaurantSlug, map);
        if (!branchId) {
          toast.error('Restaurant not found');
          router.push('/');
          return;
        }

        // Fetch branch details
        const branchData = await getBranch(branchId);
        if (!branchData.is_active) {
          toast.error('This restaurant is currently closed');
          router.push('/');
          return;
        }
        setBranch(branchData);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load restaurant';
        toast.error(errorMessage);
        router.push('/');
      } finally {
        setIsLoading(false);
      }
    }

    if (restaurantSlug) {
      fetchBranchData();
    }
  }, [restaurantSlug, router]);

  if (isLoading) {
    return (
      <>
        <Navbar />
        <LoadingPage />
      </>
    );
  }

  if (!branch) {
    return null;
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
              <div className="flex items-center gap-4 text-sm text-secondary-500">
                <span>
                  Hours: {branch.opening_time.substring(0, 5)} - {branch.closing_time.substring(0, 5)}
                </span>
                <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">
                  Open
                </span>
              </div>
            </CardContent>
          </Card>

          {!selectedTable ? (
            <TableSelection
              branch={branch}
              onTableSelect={(table) => setSelectedTable(table)}
            />
          ) : (
            <ReservationForm
              branch={branch}
              table={selectedTable}
              onBack={() => setSelectedTable(null)}
            />
          )}
        </div>
      </div>
    </>
  );
}
