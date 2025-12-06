
import { API_BASE as API_BASE_URL } from './api';

export interface QualityStats {
    total_members: number;
    total_filings: number;
    flagged_members: number;
    avg_quality_score: number;
    last_updated: string;
}

export interface QualityMember {
    bioguide_id: string;
    full_name: string;
    party: string;
    state: string;
    district?: string;
    total_filings: number;
    image_pdf_pct: number;
    avg_confidence_score: number;
    quality_score: number;
    quality_category: 'Excellent' | 'Good' | 'Fair' | 'Poor';
    is_hard_to_process: boolean;
}

export interface QualityParams {
    party?: string;
    state?: string;
    category?: string;
    flagged?: boolean;
    limit?: number;
    offset?: number;
    sort?: string;
}

export async function fetchQualityStats(): Promise<QualityStats> {
    const res = await fetch(`${API_BASE_URL}/stats/quality`);
    if (!res.ok) throw new Error('Failed to fetch quality stats');
    return res.json();
}

export async function fetchQualityMembers(params: QualityParams = {}): Promise<QualityMember[]> {
    const searchParams = new URLSearchParams();
    if (params.party) searchParams.set('party', params.party);
    if (params.category) searchParams.set('category', params.category);
    if (params.flagged !== undefined) searchParams.set('flagged', params.flagged.toString());
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const res = await fetch(`${API_BASE_URL}/quality/members?${searchParams.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch quality members');
    return res.json();
}
