'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import {
    NavigationMenu,
    NavigationMenuItem,
    NavigationMenuLink,
    NavigationMenuList,
    navigationMenuTriggerStyle,
} from '@/components/ui/navigation-menu';
import { Button } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
    Sheet,
    SheetContent,
    SheetTrigger,
} from '@/components/ui/sheet';
import {
    LayoutDashboard,
    FileText,
    Users,
    TrendingUp,
    Briefcase,
    Search,
    Network,
    Zap,
    Menu,
    Building2,
    Github,
    ChevronDown
} from 'lucide-react';

const mainNavItems = [
    { href: '/', label: 'Dashboard', Icon: LayoutDashboard },
    { href: '/bills', label: 'Bills', Icon: FileText },
    { href: '/members', label: 'Members', Icon: Users },
    { href: '/transactions', label: 'Transactions', Icon: TrendingUp },
];

const lobbyingNavItems = [
    { href: '/lobbying', label: 'Explorer', Icon: Search },
    { href: '/lobbying/network', label: 'Network Graph', Icon: Network },
    { href: '/influence', label: 'Influence Tracker', Icon: Zap },
];

export function MainNav() {
    const pathname = usePathname();

    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-16 items-center px-4">
                {/* Logo */}
                <Link href="/" className="mr-6 flex items-center space-x-3">
                    <Building2 className="h-6 w-6" />
                    <div className="hidden sm:block">
                        <div className="font-bold text-base">Congress Transparency</div>
                        <div className="text-[10px] text-muted-foreground leading-tight">
                            Surfacing the Hidden Connections Between Politics and Markets
                        </div>
                    </div>
                </Link>

                {/* Desktop Navigation */}
                <NavigationMenu className="hidden md:flex">
                    <NavigationMenuList>
                        {mainNavItems.map((item) => {
                            const Icon = item.Icon;
                            return (
                                <NavigationMenuItem key={item.href}>
                                    <NavigationMenuLink asChild active={pathname === item.href}>
                                        <Link
                                            href={item.href}
                                            className={cn(
                                                navigationMenuTriggerStyle(),
                                                pathname === item.href && 'bg-accent'
                                            )}
                                        >
                                            <Icon className="mr-2 h-4 w-4" />
                                            {item.label}
                                        </Link>
                                    </NavigationMenuLink>
                                </NavigationMenuItem>
                            );
                        })}

                        {/* Lobbying Dropdown */}
                        <NavigationMenuItem>
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        className={cn(
                                            'h-10 px-4 py-2',
                                            pathname.startsWith('/lobbying') || pathname === '/influence'
                                                ? 'bg-accent'
                                                : ''
                                        )}
                                    >
                                        <Briefcase className="mr-2 h-4 w-4" />
                                        Lobbying
                                        <ChevronDown className="ml-1 h-3 w-3 opacity-50" />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="start">
                                    {lobbyingNavItems.map((item) => {
                                        const Icon = item.Icon;
                                        return (
                                            <DropdownMenuItem key={item.href} asChild>
                                                <Link href={item.href} className="flex items-center cursor-pointer">
                                                    <Icon className="mr-2 h-4 w-4" />
                                                    {item.label}
                                                </Link>
                                            </DropdownMenuItem>
                                        );
                                    })}
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </NavigationMenuItem>
                    </NavigationMenuList>
                </NavigationMenu>

                {/* Mobile Navigation */}
                <Sheet>
                    <SheetTrigger asChild className="md:hidden">
                        <Button variant="ghost" size="icon" className="mr-2">
                            <Menu className="h-5 w-5" />
                            <span className="sr-only">Toggle menu</span>
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="w-[280px]">
                        <nav className="flex flex-col gap-4">
                            <Link href="/" className="flex items-center gap-2 text-lg font-bold">
                                <Building2 className="h-5 w-5" />
                                Congress Transparency
                            </Link>
                            <div className="flex flex-col gap-1 mt-4">
                                {mainNavItems.map((item) => {
                                    const Icon = item.Icon;
                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={cn(
                                                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium hover:bg-accent transition-colors',
                                                pathname === item.href && 'bg-accent'
                                            )}
                                        >
                                            <Icon className="h-4 w-4" />
                                            {item.label}
                                        </Link>
                                    );
                                })}
                                <div className="border-t my-2" />
                                <span className="px-3 text-sm font-medium text-muted-foreground">Lobbying</span>
                                {lobbyingNavItems.map((item) => {
                                    const Icon = item.Icon;
                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={cn(
                                                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium hover:bg-accent transition-colors',
                                                pathname === item.href && 'bg-accent'
                                            )}
                                        >
                                            <Icon className="h-4 w-4" />
                                            {item.label}
                                        </Link>
                                    );
                                })}
                            </div>
                        </nav>
                    </SheetContent>
                </Sheet>

                {/* Spacer */}
                <div className="flex-1" />

                {/* Right side actions */}
                <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" asChild>
                        <a
                            href="https://github.com/Jakeintech/congress-disclosures-standardized"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-2"
                        >
                            <Github className="h-4 w-4" />
                            <span className="hidden sm:inline">GitHub</span>
                        </a>
                    </Button>
                </div>
            </div>
        </header>
    );
}
