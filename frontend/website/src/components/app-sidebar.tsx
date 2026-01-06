'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    BarChart3,
    Building2,
    FileText,
    Home,
    Network,
    TrendingUp,
    Users,
    DollarSign,
    Settings,
    GitBranch,
    Radar,
} from 'lucide-react';

import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
} from '@/components/ui/sidebar';

const navigation = [
    {
        title: 'Overview',
        items: [
            {
                title: 'Dashboard',
                url: '/',
                icon: Home,
            },
        ],
    },
    {
        title: 'Congress',
        items: [
            {
                title: 'Members',
                url: '/members',
                icon: Users,
            },
            {
                title: 'Bills & Legislation',
                url: '/bills',
                icon: FileText,
            },
            {
                title: 'Committees',
                url: '/committees',
                icon: Building2,
            },
        ],
    },
    {
        title: 'Financial Activity',
        items: [
            {
                title: 'Trading Activity',
                url: '/transactions',
                icon: TrendingUp,
            },
        ],
    },
    {
        title: 'Analysis & Networks',
        items: [
            {
                title: 'Analytics Dashboard',
                url: '/analytics',
                icon: BarChart3,
                description: 'Comprehensive Metrics',
            },
            {
                title: 'Network Analysis',
                url: '/analysis/networks',
                icon: Network,
                description: 'Trading, Lobbying & Influence',
            },
        ],
    },
];

export function AppSidebar() {
    const pathname = usePathname();

    return (
        <Sidebar>
            <SidebarHeader className="border-b px-6 py-4">
                <Link href="/" className="flex items-center gap-2 font-semibold text-lg">
                    <Building2 className="h-6 w-6" />
                    <span>Congress Activity</span>
                </Link>
            </SidebarHeader>
            <SidebarContent>
                {navigation.map((group) => (
                    <SidebarGroup key={group.title}>
                        <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
                        <SidebarGroupContent>
                            <SidebarMenu>
                                {group.items.map((item) => {
                                    const isActive = pathname === item.url;
                                    return (
                                        <SidebarMenuItem key={item.title}>
                                            <SidebarMenuButton asChild isActive={isActive}>
                                                <Link href={item.url}>
                                                    <item.icon className="h-4 w-4" />
                                                    <span>{item.title}</span>
                                                </Link>
                                            </SidebarMenuButton>
                                        </SidebarMenuItem>
                                    );
                                })}
                            </SidebarMenu>
                        </SidebarGroupContent>
                    </SidebarGroup>
                ))}
            </SidebarContent>
            <SidebarFooter className="border-t p-4">
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton asChild>
                            <Link href="/settings">
                                <Settings className="h-4 w-4" />
                                <span>Settings</span>
                            </Link>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
                <div className="mt-4 text-xs text-muted-foreground px-2">
                    <p>Open Source Project</p>
                    <p>Data from Congress.gov</p>
                </div>
            </SidebarFooter>
        </Sidebar>
    );
}
