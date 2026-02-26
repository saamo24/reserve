'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { getBranches } from '@/lib/api';
import { BranchResponse } from '@/lib/types';
import { slugify } from '@/lib/utils';
import { Card, CardContent } from '@/components/ui/card';
import { Navbar } from '@/components/Navbar';
import { LoadingPage } from '@/components/ui/loading';
import { EmptyState } from '@/components/ui/empty-state';
import toast from 'react-hot-toast';

export default function HomePage() {
  const router = useRouter();
  const [branches, setBranches] = useState<BranchResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchBranches() {
      try {
        setIsLoading(true);
        const data = await getBranches();
        setBranches(data);
        
        // If there's exactly one branch, automatically redirect to it
        if (data.length === 1) {
          const branch = data[0];
          router.push(`/${slugify(branch.name)}`);
          return;
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load branches';
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    }

    fetchBranches();
  }, [router]);

  if (isLoading) {
    return (
      <>
        <Navbar />
        <LoadingPage />
      </>
    );
  }

  // If there's exactly one branch, show loading while redirecting
  if (branches.length === 1) {
    return (
      <>
        <Navbar />
        <LoadingPage />
      </>
    );
  }

  if (error || branches.length === 0) {
    return (
      <>
        <Navbar />
        <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-6 sm:py-8 md:py-12">
          <EmptyState
            title="No restaurants available"
            description="There are currently no restaurants available for reservations. Please check back later."
          />
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-secondary-50">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-6 sm:py-8 md:py-12">
          <div className="text-center mb-8 sm:mb-12">
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-secondary-900 mb-3 sm:mb-4">
              Welcome to Reserve
            </h1>
            <p className="text-base sm:text-lg text-secondary-600 max-w-2xl mx-auto px-4">
              Select a restaurant to make a reservation
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {branches.map((branch) => (
              <Link key={branch.id} href={`/${slugify(branch.name)}`}>
                <Card variant="elevated" className="h-full hover:shadow-lg transition-shadow cursor-pointer">
                  <CardContent className="p-4 sm:p-6">
                    <h2 className="text-lg sm:text-xl font-semibold text-secondary-900 mb-2">
                      {branch.name}
                    </h2>
                    <p className="text-sm sm:text-base text-secondary-600 mb-3 sm:mb-4">{branch.address}</p>
                    <div className="flex items-center justify-between text-xs sm:text-sm text-secondary-500">
                      <span>
                        {branch.opening_time.substring(0, 5)} - {branch.closing_time.substring(0, 5)}
                      </span>
                      <span className="px-2 py-1 bg-primary-100 text-primary-700 rounded-full text-xs font-medium">
                        {branch.is_active ? 'Open' : 'Closed'}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
