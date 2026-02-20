'use client';

import React, { useEffect, useState } from 'react';
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
  const [branches, setBranches] = useState<BranchResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchBranches() {
      try {
        setIsLoading(true);
        const data = await getBranches();
        setBranches(data);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load branches';
        setError(errorMessage);
        toast.error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    }

    fetchBranches();
  }, []);

  if (isLoading) {
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold text-secondary-900 mb-4">
              Welcome to Reserve
            </h1>
            <p className="text-lg text-secondary-600 max-w-2xl mx-auto">
              Select a restaurant to make a reservation
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {branches.map((branch) => (
              <Link key={branch.id} href={`/${slugify(branch.name)}`}>
                <Card variant="elevated" className="h-full hover:shadow-lg transition-shadow cursor-pointer">
                  <CardContent className="p-6">
                    <h2 className="text-xl font-semibold text-secondary-900 mb-2">
                      {branch.name}
                    </h2>
                    <p className="text-secondary-600 mb-4">{branch.address}</p>
                    <div className="flex items-center justify-between text-sm text-secondary-500">
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
