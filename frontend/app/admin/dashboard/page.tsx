'use client';

import React, { useEffect, useState } from 'react';
import { getDashboardStats } from '@/lib/api';
import { DashboardStats } from '@/lib/types';
import { StatsCard } from '@/components/StatsCard';
import { LoadingPage } from '@/components/ui/loading';
import toast from 'react-hot-toast';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        setIsLoading(true);
        const response = await getDashboardStats();
        setStats(response.data);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load dashboard stats';
        toast.error(errorMessage);
      } finally {
        setIsLoading(false);
      }
    }

    fetchStats();
  }, []);

  if (isLoading) {
    return <LoadingPage />;
  }

  if (!stats) {
    return (
      <div className="text-center py-12">
        <p className="text-secondary-600">No data available</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-secondary-900">Dashboard</h1>
        <p className="text-secondary-600 mt-2">Overview of your restaurant reservations</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Reservations"
          value={stats.total_reservations}
          description="All time reservations"
          icon="📊"
        />
        <StatsCard
          title="Active Reservations"
          value={stats.active_reservations}
          description="Confirmed and pending"
          icon="✅"
        />
        <StatsCard
          title="Upcoming Reservations"
          value={stats.upcoming_reservations}
          description="Today and future"
          icon="📅"
        />
        <StatsCard
          title="Occupancy Rate"
          value={`${stats.occupancy_rate_percent}%`}
          description="Current utilization"
          icon="📈"
        />
      </div>
    </div>
  );
}
