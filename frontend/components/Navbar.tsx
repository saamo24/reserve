import React from 'react';
import Link from 'next/link';

export function Navbar() {
  return (
    <nav className="bg-white border-b border-secondary-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8">
        <div className="flex justify-between items-center h-14 sm:h-16">
          <Link href="/" className="text-xl sm:text-2xl font-bold text-primary-600">
            Reserve
          </Link>
          <div className="flex items-center space-x-2 sm:space-x-4">
            <Link
              href="/my-reservations"
              className="text-xs sm:text-sm text-secondary-600 hover:text-secondary-900 transition-colors whitespace-nowrap"
            >
              <span className="hidden sm:inline">My Reservations</span>
              <span className="sm:hidden">Reservations</span>
            </Link>
            <Link
              href="/admin/login"
              className="text-xs sm:text-sm text-secondary-600 hover:text-secondary-900 transition-colors"
            >
              Admin
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
