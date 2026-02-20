'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AdminSidebar } from '@/components/AdminSidebar';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/admin/login';

  // Login page should not be protected and should not show sidebar
  if (isLoginPage) {
    return <>{children}</>;
  }

  // All other admin pages are protected
  return (
    <ProtectedRoute>
      <div className="flex h-screen bg-secondary-50">
        <AdminSidebar />
        <main className="flex-1 overflow-y-auto md:ml-64">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">{children}</div>
          </div>
        </main>
      </div>
    </ProtectedRoute>
  );
}
