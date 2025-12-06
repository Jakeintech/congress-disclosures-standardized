import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { NetworkGraph } from '@/components/lobbying/network-graph';
import { fetchNetworkGraph } from '@/lib/api';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export default async function LobbyingNetworkPage() {
    let data = null;
    let error = null;

    try {
        data = await fetchNetworkGraph();
    } catch (e) {
        console.error("Build-time fetch failed:", e);
        error = "Failed to load network data. The analysis pipeline may still be processing.";
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">Lobbying Network Graph</h1>
                <p className="text-muted-foreground">
                    Interactive visualization of connections between Members and traded assets.
                </p>
            </div>

            {error ? (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            ) : (
                <Card className="overflow-hidden">
                    <CardHeader>
                        <CardTitle>Network Visualization</CardTitle>
                        <CardDescription>
                            Nodes represent Members (Blue/Red) and Assets (Green). Links represent transaction volume.
                            Drag nodes to rearrange. Scroll to zoom.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="p-0">
                        {/* Ensure data is present before rendering client component */}
                        {data && <NetworkGraph data={data} width={1000} height={700} />}
                        {!data && (
                            <div className="p-8 text-center text-muted-foreground">
                                No network data available.
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
