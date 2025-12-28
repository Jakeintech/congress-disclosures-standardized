'use client';

import { useEffect, useRef } from 'react';
import { useRecentActivity } from '@/hooks/use-api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { toast } from 'sonner';
import { FileText, TrendingUp, Users, Clock, Briefcase } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';

export function RecentActivityFeed() {
    const { data: activity, isLoading, isError } = useRecentActivity();
    const lastActivityId = useRef<string | null>(null);

    // Toast notifications for new activity
    useEffect(() => {
        if (activity && activity.length > 0) {
            const latest = activity[0];
            const currentId = `${latest.type}-${latest.date}-${latest.subject}`;

            if (lastActivityId.current && lastActivityId.current !== currentId) {
                // New activity detected
                toast.success(`New Activity: ${latest.type.toUpperCase()}`, {
                    description: `${latest.actor || ''} ${latest.action} ${latest.subject}`,
                    duration: 5000,
                });
            }
            lastActivityId.current = currentId;
        }
    }, [activity]);

    if (isLoading) {
        return (
            <Card className="h-full">
                <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Clock className="w-5 h-5" />
                        Recent Activity
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-4">
                        {[1, 2, 3, 4, 5].map((i) => (
                            <div key={i} className="flex gap-3">
                                <Skeleton className="w-10 h-10 rounded-full" />
                                <div className="space-y-2 flex-1">
                                    <Skeleton className="h-4 w-full" />
                                    <Skeleton className="h-3 w-2/3" />
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>
        );
    }

    if (isError) {
        return (
            <Card className="h-full">
                <CardContent className="pt-6 text-center text-muted-foreground">
                    Failed to load activity feed.
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="h-full">
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
                <CardTitle className="text-lg flex items-center gap-2">
                    <Clock className="w-5 h-5" />
                    Recent Activity
                </CardTitle>
                <Badge variant="outline" className="font-normal">Live</Badge>
            </CardHeader>
            <CardContent>
                <ScrollArea className="h-[400px] pr-4">
                    <div className="space-y-6">
                        {activity?.map((item: any, idx: number) => (
                            <ActivityItem key={idx} item={item} />
                        ))}
                        {(!activity || activity.length === 0) && (
                            <div className="text-center py-12 text-muted-foreground italic">
                                No recent activity found.
                            </div>
                        )}
                    </div>
                </ScrollArea>
            </CardContent>
        </Card>
    );
}

function ActivityItem({ item }: { item: any }) {
    const Icon = item.type === 'trade' ? TrendingUp :
        item.type === 'bill' ? FileText :
            item.type === 'lobbying' ? Briefcase : Users;

    const colorClass = item.type === 'trade' ? 'text-green-500 bg-green-500/10' :
        item.type === 'bill' ? 'text-blue-500 bg-blue-500/10' :
            item.type === 'lobbying' ? 'text-purple-500 bg-purple-500/10' :
                'text-gray-500 bg-gray-500/10';

    const date = new Date(item.date);
    const timeAgo = formatDistanceToNow(date, { addSuffix: true });

    return (
        <div className="flex gap-4 group">
            <div className={`p-2 rounded-full h-10 w-10 flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                <Icon className="w-5 h-5" />
            </div>
            <div className="flex-1 space-y-1">
                <p className="text-sm leading-none">
                    <span className="font-semibold">{item.actor || 'System'}</span>
                    {' '}
                    <span className="text-muted-foreground">{item.action}</span>
                    {' '}
                    <span className="font-medium text-foreground">{item.subject}</span>
                </p>
                <div className="flex items-center gap-2">
                    <p className="text-xs text-muted-foreground">
                        {timeAgo}
                    </p>
                    {item.detail && (
                        <>
                            <span className="text-muted-foreground text-[10px]">•</span>
                            <Badge variant="secondary" className="text-[10px] h-4 px-1 leading-none font-normal">
                                {item.detail}
                            </Badge>
                        </>
                    )}
                </div>
                {item.type === 'trade' && item.actor_id && (
                    <Link
                        href={`/politician/${item.actor_id}`}
                        className="text-[10px] text-primary hover:underline block"
                    >
                        View Profile
                    </Link>
                )}
                {item.type === 'bill' && item.subject_id && (
                    <Link
                        href={`/bills/${item.subject_id.split('-').join('/')}`}
                        className="text-[10px] text-primary hover:underline block"
                    >
                        View Bill Detail
                    </Link>
                )}
            </div>
        </div>
    );
}
