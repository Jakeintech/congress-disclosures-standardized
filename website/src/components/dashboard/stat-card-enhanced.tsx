'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { LucideIcon } from 'lucide-react';

interface StatCardEnhancedProps {
  title: string;
  value: string | number;
  change?: string | number;
  trend?: 'up' | 'down' | 'neutral';
  icon: LucideIcon;
  loading?: boolean;
  subtitle?: string;
}

export function StatCardEnhanced({
  title,
  value,
  change,
  trend,
  icon: Icon,
  loading,
  subtitle
}: StatCardEnhancedProps) {
  const getTrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      case 'down':
        return <TrendingDown className="h-4 w-4 text-red-500" />;
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'text-green-600 dark:text-green-400';
      case 'down':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-8 w-24" />
            {change && <Skeleton className="h-4 w-16" />}
          </div>
        ) : (
          <>
            <div className="text-2xl font-bold">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </div>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-1">
                {subtitle}
              </p>
            )}
            {change && (
              <div className={`flex items-center gap-1 text-xs mt-1 ${getTrendColor()}`}>
                {getTrendIcon()}
                <span className="font-medium">{change}</span>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
