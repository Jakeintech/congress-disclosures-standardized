'use client';

import { useState, useEffect } from 'react';
import {
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
    Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbSeparator
} from '@/components/ui/breadcrumb';
import { FolderIcon, FileIcon, DownloadIcon } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

// Use same base as other components
const API_BASE = 'https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com';

interface S3Item {
    name: string;
    type: 'directory' | 'file';
    path: string;
    size?: number;
    last_modified?: string;
}

interface S3BrowserProps {
    initialLayer?: string;
}

export function S3Browser({ initialLayer = 'bronze' }: S3BrowserProps) {
    const [layer, setLayer] = useState(initialLayer);
    const [prefix, setPrefix] = useState('');
    const [items, setItems] = useState<S3Item[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch data
    useEffect(() => {
        async function load() {
            setLoading(true);
            setError(null);
            try {
                // v1/storage/{layer}?prefix={prefix}
                const url = `${API_BASE}/v1/storage/${layer}?prefix=${encodeURIComponent(prefix)}`;
                const res = await fetch(url);
                if (!res.ok) throw new Error('Failed to load S3 content');

                const data = await res.json();
                // API returns { success: true, data: { files: [], directories: [] } } or similar
                // Adapting based on likely structure from legacy s3_browser.js usage
                const content = data.data || data;

                const dirs: S3Item[] = (content.directories || []).map((d: any) => ({
                    name: d.name || d,
                    type: 'directory',
                    path: d.prefix || d.path || d
                }));

                const files: S3Item[] = (content.files || []).map((f: any) => ({
                    name: f.name || f.key || f,
                    type: 'file',
                    path: f.key || f.path || f,
                    size: f.size,
                    last_modified: f.last_modified
                }));

                setItems([...dirs, ...files]);
            } catch (err) {
                console.error(err);
                setError('Failed to load directory listing');
            } finally {
                setLoading(false);
            }
        }

        load();
    }, [layer, prefix]);

    // Handle navigation
    const navigateTo = (path: string) => {
        setPrefix(path);
    };

    const navigateUp = () => {
        if (!prefix) return;
        const parts = prefix.split('/').filter(p => p);
        if (parts.length <= 1) {
            setPrefix('');
        } else {
            parts.pop();
            setPrefix(parts.join('/') + '/');
        }
    };

    const breadcrumbs = prefix.split('/').filter(p => p);

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex gap-2">
                    {['bronze', 'silver', 'gold'].map((l) => (
                        <Button
                            key={l}
                            variant={layer === l ? 'default' : 'outline'}
                            onClick={() => { setLayer(l); setPrefix(''); }}
                            className="capitalize"
                        >
                            {l}
                        </Button>
                    ))}
                </div>
            </div>

            <div className="bg-muted/30 p-2 rounded-md border">
                <Breadcrumb>
                    <BreadcrumbList>
                        <BreadcrumbItem>
                            <BreadcrumbLink onClick={() => setPrefix('')} className="cursor-pointer font-bold">
                                {layer.toUpperCase()}
                            </BreadcrumbLink>
                        </BreadcrumbItem>
                        {breadcrumbs.map((part, idx) => {
                            const pathSoFar = breadcrumbs.slice(0, idx + 1).join('/') + '/';
                            return (
                                <div key={pathSoFar} className="flex items-center">
                                    <BreadcrumbSeparator />
                                    <BreadcrumbItem>
                                        <BreadcrumbLink onClick={() => setPrefix(pathSoFar)} className="cursor-pointer">
                                            {part}
                                        </BreadcrumbLink>
                                    </BreadcrumbItem>
                                </div>
                            );
                        })}
                    </BreadcrumbList>
                </Breadcrumb>
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[50px]"></TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead className="text-right">Size</TableHead>
                            <TableHead className="text-right">Last Modified</TableHead>
                            <TableHead className="w-[50px]"></TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {prefix && (
                            <TableRow className="hover:bg-muted/50 cursor-pointer" onClick={navigateUp}>
                                <TableCell><FolderIcon className="h-4 w-4 text-muted-foreground" /></TableCell>
                                <TableCell colSpan={4} className="font-medium text-muted-foreground">..</TableCell>
                            </TableRow>
                        )}

                        {loading ? (
                            [...Array(3)].map((_, i) => (
                                <TableRow key={i}>
                                    <TableCell><Skeleton className="h-4 w-4" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-10 ml-auto" /></TableCell>
                                    <TableCell><Skeleton className="h-4 w-20 ml-auto" /></TableCell>
                                    <TableCell></TableCell>
                                </TableRow>
                            ))
                        ) : items.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                                    Empty directory
                                </TableCell>
                            </TableRow>
                        ) : (
                            items.map((item) => (
                                <TableRow
                                    key={item.path}
                                    className={item.type === 'directory' ? 'cursor-pointer hover:bg-muted/50' : ''}
                                    onClick={() => item.type === 'directory' && navigateTo(item.path)}
                                >
                                    <TableCell>
                                        {item.type === 'directory' ?
                                            <FolderIcon className="h-4 w-4 text-blue-500" /> :
                                            <FileIcon className="h-4 w-4 text-slate-500" />
                                        }
                                    </TableCell>
                                    <TableCell className="font-medium">{item.name}</TableCell>
                                    <TableCell className="text-right text-xs font-mono">
                                        {item.size ? formatBytes(item.size) : '-'}
                                    </TableCell>
                                    <TableCell className="text-right text-xs text-muted-foreground">
                                        {item.last_modified ? new Date(item.last_modified).toLocaleDateString() : '-'}
                                    </TableCell>
                                    <TableCell>
                                        {item.type === 'file' && (
                                            <Button variant="ghost" size="icon" asChild>
                                                <a href={`https://${layer === 'gold' ? 'congress-disclosures-standardized' : 'congress-disclosures-standardized'}.s3.us-east-1.amazonaws.com/${layer}/${item.path}`} target="_blank" rel="noopener noreferrer">
                                                    <DownloadIcon className="h-4 w-4" />
                                                </a>
                                            </Button>
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}

function formatBytes(bytes: number, decimals = 2) {
    if (!+bytes) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}
