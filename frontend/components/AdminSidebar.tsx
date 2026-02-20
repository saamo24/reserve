'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { cn } from '@/lib/utils';

const navigation = [
  { name: 'Dashboard', href: '/admin/dashboard', icon: '📊' },
  { name: 'Reservations', href: '/admin/reservations', icon: '📅' },
  { name: 'Branches', href: '/admin/branches', icon: '🏢' },
  { name: 'Tables', href: '/admin/tables', icon: '🪑' },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <div className="hidden md:flex md:w-64 md:flex-col md:fixed md:inset-y-0">
      <div className="flex-1 flex flex-col min-h-0 bg-white border-r border-secondary-200">
        <div className="flex-1 flex flex-col pt-5 pb-4 overflow-y-auto">
          <div className="flex items-center flex-shrink-0 px-4 mb-8">
            <h1 className="text-2xl font-bold text-primary-600">Reserve</h1>
          </div>
          <nav className="mt-5 flex-1 px-2 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'group flex items-center px-3 py-2 text-sm font-medium rounded-xl transition-all duration-200',
                    isActive
                      ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600'
                      : 'text-secondary-700 hover:bg-secondary-50 hover:text-secondary-900'
                  )}
                >
                  <span className="mr-3 text-lg">{item.icon}</span>
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="flex-shrink-0 flex border-t border-secondary-200 p-4">
          <button
            onClick={logout}
            className="flex-shrink-0 w-full group block rounded-xl p-3 text-secondary-700 hover:bg-secondary-50 transition-colors"
          >
            <div className="flex items-center">
              <span className="mr-3 text-lg">🚪</span>
              <span className="text-sm font-medium">Logout</span>
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
