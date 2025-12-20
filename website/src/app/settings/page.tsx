"use client"

import { Metadata } from "next";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { useTheme } from "next-themes";
import { Moon, Sun, Monitor, RefreshCw, Info } from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
    const { theme, setTheme } = useTheme();
    const [mounted, setMounted] = useState(false);

    // useEffect(() => setMounted(true), [])
    // Simplified: just check if we're in browser
    const isMounted = typeof window !== 'undefined';

    return (
        <div className="space-y-8 max-w-4xl">
            {/* Page Header */}
            <div>
                <h1 className="text-3xl font-bold  tracking-tight">Settings</h1>
                <p className="text-muted-foreground mt-2">
                    Manage your preferences and application settings
                </p>
            </div>

            {/* Appearance Settings */}
            <Card>
                <CardHeader>
                    <CardTitle>Appearance</CardTitle>
                    <CardDescription>
                        Customize how the application looks and feels
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-3">
                        <Label>Theme</Label>
                        <p className="text-sm text-muted-foreground">
                            Select your preferred color scheme
                        </p>
                        <div className="grid grid-cols-3 gap-3">
                            <Button
                                variant={theme === "light" ? "default" : "outline"}
                                className="justify-start"
                                onClick={() => setTheme("light")}
                                disabled={!isMounted}
                            >
                                <Sun className="mr-2 h-4 w-4" />
                                Light
                            </Button>
                            <Button
                                variant={theme === "dark" ? "default" : "outline"}
                                className="justify-start"
                                onClick={() => setTheme("dark")}
                                disabled={!isMounted}
                            >
                                <Moon className="mr-2 h-4 w-4" />
                                Dark
                            </Button>
                            <Button
                                variant={theme === "system" ? "default" : "outline"}
                                className="justify-start"
                                onClick={() => setTheme("system")}
                                disabled={!isMounted}
                            >
                                <Monitor className="mr-2 h-4 w-4" />
                                System
                            </Button>
                        </div>
                        {!isMounted && (
                            <p className="text-xs text-muted-foreground">
                                Loading theme preferences...
                            </p>
                        )}
                    </div>
                </CardContent>
            </Card>

            {/* Data & Cache Settings */}
            <Card>
                <CardHeader>
                    <CardTitle>Data & Cache</CardTitle>
                    <CardDescription>
                        Manage data refresh and caching preferences
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-3">
                        <Label>Data Refresh</Label>
                        <p className="text-sm text-muted-foreground">
                            API data is cached for performance. Last updated: <span className="font-mono">2025-12-11 09:00 UTC</span>
                        </p>
                        <Button variant="outline" size="sm">
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Clear Cache & Refresh
                        </Button>
                    </div>

                    <Separator />

                    <div className="space-y-3">
                        <Label>Automatic Updates</Label>
                        <p className="text-sm text-muted-foreground">
                            Data is automatically updated daily via GitHub Actions. Next update: ~24 hours
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Display Preferences (Placeholder for future) */}
            <Card>
                <CardHeader>
                    <CardTitle>Display Preferences</CardTitle>
                    <CardDescription>
                        Customize tables, charts, and visualizations (Coming Soon)
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <div className="space-y-3">
                        <Label className="text-muted-foreground">Table Density</Label>
                        <p className="text-sm text-muted-foreground">
                            Compact, Standard, or Comfortable (Phase 2)
                        </p>
                    </div>

                    <Separator />

                    <div className="space-y-3">
                        <Label className="text-muted-foreground">Default Date Range</Label>
                        <p className="text-sm text-muted-foreground">
                            30, 90, 180, or 365 days (Phase 2)
                        </p>
                    </div>

                    <Separator />

                    <div className="space-y-3">
                        <Label className="text-muted-foreground">Chart Style</Label>
                        <p className="text-sm text-muted-foreground">
                            Line, Bar, or Area charts (Phase 2)
                        </p>
                    </div>
                </CardContent>
            </Card>

            {/* Notifications (Future Feature) */}
            <Card className="border-dashed">
                <CardHeader>
                    <CardTitle className="text-base">🔔 Notifications (Coming Soon)</CardTitle>
                    <CardDescription>
                        Phase 5 will add email alerts and webhooks for:
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <ul className="text-sm text-muted-foreground space-y-2 ml-4 list-disc">
                        <li>New trades from followed members</li>
                        <li>Bill progress updates</li>
                        <li>Conflict alerts (high-severity)</li>
                        <li>Trading pattern anomalies</li>
                        <li>Custom watchlist triggers</li>
                    </ul>
                </CardContent>
            </Card>

            {/* About Section */}
            <Card>
                <CardHeader>
                    <CardTitle>About</CardTitle>
                    <CardDescription>
                        Platform information and data sources
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="flex items-start gap-3">
                        <Info className="h-5 w-5 text-muted-foreground mt-0.5" />
                        <div className="space-y-1">
                            <p className="text-sm font-medium">Congress Activity Platform</p>
                            <p className="text-sm text-muted-foreground">Version 1.0.0 (Phase 1)</p>
                        </div>
                    </div>

                    <Separator />

                    <div className="space-y-2">
                        <p className="text-sm font-medium">Data Sources</p>
                        <ul className="text-sm text-muted-foreground space-y-1 ml-4 list-disc">
                            <li>House Clerk Financial Disclosures (Bronze Layer)</li>
                            <li>Congress.gov API (Bills, Committees, Members)</li>
                            <li>Senate Lobbying Disclosure Database</li>
                            <li>Historical data: 2019-2025</li>
                        </ul>
                    </div>

                    <Separator />

                    <div className="space-y-2">
                        <p className="text-sm font-medium">Legal</p>
                        <div className="flex gap-4 text-sm text-muted-foreground">
                            <a href="/legal/basis" className="hover:underline">Legal Basis</a>
                            <a href="/legal/terms" className="hover:underline">Terms</a>
                            <a href="/legal/privacy" className="hover:underline">Privacy</a>
                            <a href="/legal/api-terms" className="hover:underline">API Terms</a>
                        </div>
                    </div>

                    <Separator />

                    <div className="space-y-2">
                        <p className="text-sm font-medium">Open Source</p>
                        <p className="text-sm text-muted-foreground">
                            This platform is 100% open source.{" "}
                            <a
                                href="https://github.com/Jakeintech/congress-disclosures-standardized"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline"
                            >
                                View on GitHub →
                            </a>
                        </p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
