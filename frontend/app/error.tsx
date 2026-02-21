'use client';

import React, { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-secondary-50 flex items-center justify-center px-4">
      <Card variant="elevated" className="max-w-md w-full">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <span className="text-3xl">⚠️</span>
          </div>
          <CardTitle className="text-2xl">Something went wrong!</CardTitle>
        </CardHeader>
        <CardContent className="text-center space-y-4">
          <p className="text-secondary-600">{error.message || 'An unexpected error occurred'}</p>
          <div className="flex gap-4 justify-center">
            <Button variant="outline" onClick={() => window.location.href = '/'}>
              Go Home
            </Button>
            <Button variant="primary" onClick={reset}>
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
