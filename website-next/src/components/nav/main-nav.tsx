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

const mainNavItems = [
    { href: '/', label: 'Dashboard', icon: '📊' },
    { href: '/bills', label: 'Bills', icon: '📜' },
    { href: '/members', label: 'Members', icon: '👥' },
    { href: '/transactions', label: 'Transactions', icon: '💰' },
];

const lobbyingNavItems = [
    { href: '/lobbying', label: 'Explorer', icon: '🔍' },
    { href: '/lobbying/network', label: 'Network Graph', icon: '🕸️' },
    { href: '/influence', label: 'Influence Tracker', icon: '⚡' },
];

export function MainNav() {
    const pathname = usePathname();

    return (
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="container flex h-14 items-center">
                {/* Logo */}
                <Link href="/" className="mr-6 flex items-center space-x-2">
                    <span className="text-xl">🏛️</span>
                    <span className="hidden font-bold sm:inline-block">
                        Congress Disclosures
                    </span>
                </Link>

                {/* Desktop Navigation */}
                <NavigationMenu className="hidden md:flex">
                    <NavigationMenuList>
                        {mainNavItems.map((item) => (
                            <NavigationMenuItem key={item.href}>
                                <NavigationMenuLink asChild active={pathname === item.href}>
                                    <Link
                                        href={item.href}
                                        className={cn(
                                            navigationMenuTriggerStyle(),
                                            pathname === item.href && 'bg-accent'
                                        )}
                                    >
                                        <span className="mr-1">{item.icon}</span>
                                        {item.label}
                                    </Link>
                                </NavigationMenuLink>
                            </NavigationMenuItem>
                        ))}

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
                                        <span className="mr-1">💼</span>
                                        Lobbying
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="start">
                                    {lobbyingNavItems.map((item) => (
                                        <DropdownMenuItem key={item.href} asChild>
                                            <Link href={item.href} className="flex items-center">
                                                <span className="mr-2">{item.icon}</span>
                                                {item.label}
                                            </Link>
                                        </DropdownMenuItem>
                                    ))}
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </NavigationMenuItem>
                    </NavigationMenuList>
                </NavigationMenu>

                {/* Mobile Navigation */}
                <Sheet>
                    <SheetTrigger asChild className="md:hidden">
                        <Button variant="ghost" size="icon" className="mr-2">
                            <span className="text-xl">☰</span>
                            <span className="sr-only">Toggle menu</span>
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="w-[240px]">
                        <nav className="flex flex-col gap-4 mt-4">
                            <Link href="/" className="flex items-center gap-2 text-lg font-bold">
                                <span>🏛️</span>
                                Congress Disclosures
                            </Link>
                            <div className="flex flex-col gap-2 mt-4">
                                {mainNavItems.map((item) => (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        className={cn(
                                            'flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent',
                                            pathname === item.href && 'bg-accent'
                                        )}
                                    >
                                        <span>{item.icon}</span>
                                        {item.label}
                                    </Link>
                                ))}
                                <div className="border-t my-2" />
                                <span className="px-3 text-sm text-muted-foreground">Lobbying</span>
                                {lobbyingNavItems.map((item) => (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        className={cn(
                                            'flex items-center gap-2 px-3 py-2 rounded-md hover:bg-accent',
                                            pathname === item.href && 'bg-accent'
                                        )}
                                    >
                                        <span>{item.icon}</span>
                                        {item.label}
                                    </Link>
                                ))}
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
                        >
                            GitHub
                        </a>
                    </Button>
                </div>
            </div>
        </header>
    );
}
