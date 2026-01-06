'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { InfluenceTracker } from '@/components/analysis/influence-tracker';
import { AlertCircle, Info } from 'lucide-react';
import { useState } from 'react';

export default function InfluenceTrackerPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Influence Tracker</h1>
                <p className="text-muted-foreground mt-2">
                    Advanced correlation analysis connecting congressional trades, legislative bills, and lobbying activity.
                    Discover potential conflicts of interest and influence patterns.
                </p>
            </div>

            <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                    This tool analyzes triple correlations between member trades, bill actions, and lobbying disclosures.
                    Scores indicate the strength and timing of connections. Higher scores suggest stronger potential relationships.
                </AlertDescription>
            </Alert>

            <InfluenceTracker />

            {/* Feature explanation cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Correlation Scoring</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground space-y-2">
                        <p><strong>100:</strong> Perfect match - Multiple indicators align</p>
                        <p><strong>80-99:</strong> Very Strong - Clear temporal and subject correlation</p>
                        <p><strong>60-79:</strong> Strong - Significant lobbying activity on related bill</p>
                        <p><strong>40-59:</strong> Moderate - Some connection indicators present</p>
                        <p><strong>&lt;40:</strong> Weak - Limited correlation signals</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">What We Analyze</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground space-y-2">
                        <p>• <strong>Multi-client interest:</strong> How many organizations are lobbying</p>
                        <p>• <strong>Filing activity:</strong> Frequency of lobbying disclosures</p>
                        <p>• <strong>Lobbying spend:</strong> Dollar amounts invested in influence</p>
                        <p>• <strong>Firm diversity:</strong> Number of different lobbying firms hired</p>
                        <p>• <strong>Timing analysis:</strong> Temporal proximity of trades to bill actions</p>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">Stock Impact Predictions</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground space-y-2">
                        <p>Based on lobbying issue codes and client profiles, we predict which stocks may be affected by legislation.</p>
                        <p><strong>Defense bills</strong> → LMT, RTX, NOC, GD</p>
                        <p><strong>Healthcare bills</strong> → UNH, PFE, CVS</p>
                        <p><strong>Energy bills</strong> → XOM, CVX, NEE</p>
                        <p><strong>Tech bills</strong> → AAPL, MSFT, GOOGL</p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
