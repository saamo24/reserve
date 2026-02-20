import React from 'react';
import Link from 'next/link';

export function Navbar() {
  return (
    <nav className="bg-white border-b border-secondary-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <Link href="/" className="text-2xl font-bold text-primary-600">
            Reserve
          </Link>
          <div className="flex items-center space-x-4">
            <Link
              href="/admin/login"
              className="text-secondary-600 hover:text-secondary-900 transition-colors"
            >
              Admin
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}
