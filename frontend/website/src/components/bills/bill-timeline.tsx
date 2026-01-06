'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Circle, AlertCircle, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface TimelineEvent {
  date: string;
  title: string;
  description?: string;
  status: 'completed' | 'current' | 'pending' | 'failed';
  chamber?: string;
  tradeAlert?: boolean;
  tradeCount?: number;
}

interface BillTimelineProps {
  events: TimelineEvent[];
  billId?: string;
}

export function BillTimeline({ events, billId }: BillTimelineProps) {
  const getStatusIcon = (status: TimelineEvent['status'], index: number) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />;
      case 'current':
        return (
          <div className="relative">
            <Circle className="h-5 w-5 text-blue-500 fill-blue-500" />
            <div className="absolute inset-0 animate-ping">
              <Circle className="h-5 w-5 text-blue-500" />
            </div>
          </div>
        );
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return <Circle className="h-5 w-5 text-muted-foreground" />;
    }
  };

  const getStatusColor = (status: TimelineEvent['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'current':
        return 'bg-blue-500';
      case 'failed':
        return 'bg-red-500';
      default:
        return 'bg-muted';
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bill Lifecycle Timeline</CardTitle>
        <CardDescription>
          Track the progress of this bill through Congress
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="relative space-y-6">
          {/* Vertical Line */}
          <div className="absolute left-[9px] top-2 bottom-2 w-0.5 bg-border" />

          {events.map((event, index) => (
            <div key={index} className="relative flex gap-4 group">
              {/* Icon */}
              <div className="relative z-10 flex-shrink-0">
                {getStatusIcon(event.status, index)}
              </div>

              {/* Content */}
              <div className="flex-1 pb-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4
                        className={cn(
                          'font-semibold',
                          event.status === 'current' && 'text-blue-600 dark:text-blue-400',
                          event.status === 'pending' && 'text-muted-foreground'
                        )}
                      >
                        {event.title}
                      </h4>
                      {event.chamber && (
                        <Badge variant="outline" className="capitalize">
                          {event.chamber}
                        </Badge>
                      )}
                      {event.tradeAlert && event.tradeCount && (
                        <Badge variant="destructive" className="flex items-center gap-1">
                          <TrendingUp className="h-3 w-3" />
                          {event.tradeCount} trades
                        </Badge>
                      )}
                    </div>
                    {event.description && (
                      <p className="text-sm text-muted-foreground">{event.description}</p>
                    )}
                  </div>
                  <time className="text-sm text-muted-foreground whitespace-nowrap">
                    {event.date ? formatDate(event.date) : 'TBD'}
                  </time>
                </div>

                {/* Trade Alert Details */}
                {event.tradeAlert && event.tradeCount && (
                  <div className="mt-3 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                    <div className="flex items-center gap-2 text-sm text-destructive">
                      <AlertCircle className="h-4 w-4" />
                      <span className="font-medium">Trading Activity Detected</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {event.tradeCount} member{event.tradeCount > 1 ? 's' : ''} traded related
                      stocks within 7 days of this action
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Legend */}
        <div className="mt-8 pt-6 border-t">
          <p className="text-xs font-medium text-muted-foreground mb-3">Timeline Status</p>
          <div className="flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <span>Completed</span>
            </div>
            <div className="flex items-center gap-2">
              <Circle className="h-4 w-4 text-blue-500 fill-blue-500" />
              <span>Current Stage</span>
            </div>
            <div className="flex items-center gap-2">
              <Circle className="h-4 w-4 text-muted-foreground" />
              <span>Pending</span>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-destructive" />
              <span>Trade Activity Alert</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
