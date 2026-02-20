import React from 'react';
import { Card, CardContent } from './ui/card';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
}

export function StatsCard({ title, value, description, icon, trend, className }: StatsCardProps) {
  return (
    <Card variant="elevated" className={cn('', className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-secondary-600 mb-1">{title}</p>
            <p className="text-3xl font-bold text-secondary-900 mb-2">{value}</p>
            {description && <p className="text-xs text-secondary-500">{description}</p>}
            {trend && (
              <div className="flex items-center mt-2">
                <span
                  className={cn(
                    'text-xs font-medium',
                    trend.isPositive ? 'text-green-600' : 'text-red-600'
                  )}
                >
                  {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
                </span>
                <span className="text-xs text-secondary-500 ml-1">vs last period</span>
              </div>
            )}
          </div>
          {icon && (
            <div className="ml-4 p-3 bg-primary-100 rounded-xl text-primary-600 text-2xl">
              {icon}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
