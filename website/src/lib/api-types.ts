/**
 * OpenAPI Response Types
 * 
 * Standard response wrapper for all API endpoints
 */

import type { Bill } from '../types/api';
// Note: Add Trade and Member types when implementing those endpoints

export interface APIResponse<T = any> {
    success: boolean;
    data?: T;
    error?: {
        message: string;
        code?: number | string;
    };
    version?: string;
    metadata?: {
        cache_seconds?: number;
        [key: string]: any;
    };
}

/**
 * Paginated response structure
 */
export interface PaginatedData<T> {
    [key: string]: T[] | PaginationMeta; // The actual data array (e.g., 'bills', 'trades', 'members')
    pagination: PaginationMeta;
}

export interface PaginationMeta {
    total: number;
    count: number;
    limit: number;
    offset: number;
    has_next: boolean;
    has_prev: boolean;
    next: string | null;
    prev: string | null;
}

/**
 * Bills API Response
 */
export interface BillsResponse {
    bills: Bill[];
    pagination: PaginationMeta;
}

/**
 * Trades API Response
 * TODO: Implement when refactoring trades endpoint
 */
// export interface TradesResponse {
//     trades: Trade[];
//     pagination: PaginationMeta;
// }

/**
 * Members API Response  
 * TODO: Implement when refactoring members endpoint
 */
// export interface MembersResponse {
//     members: Member[];
//     pagination: PaginationMeta;
// }

/**
 * Type guard to check if response is paginated
 */
export function isPaginatedResponse(data: any): data is PaginatedData<any> {
    return data && typeof data === 'object' && 'pagination' in data;
}

/**
 * Extract items from a paginated response
 * Automatically detects the data array key
 */
export function extractPaginatedItems<T>(response: PaginatedData<T>): T[] {
    // Find the key that contains the array (not 'pagination')
    const dataKey = Object.keys(response).find(
        key => key !== 'pagination' && Array.isArray(response[key])
    );

    if (!dataKey) {
        console.warn('No data array found in paginated response', response);
        return [];
    }

    return response[dataKey] as T[];
}

/**
 * Type-safe API response parser
 */
export function parseAPIResponse<T>(
    raw: any,
    options: {
        expectArray?: boolean;
        expectPaginated?: boolean;
        dataKey?: string;
    } = {}
): T | T[] {
    // Handle direct array responses (legacy)
    if (Array.isArray(raw)) {
        return raw as T[];
    }

    // Handle standard API response wrapper
    if (raw && typeof raw === 'object' && 'data' in raw) {
        const data = raw.data;

        // If expecting paginated response
        if (options.expectPaginated && isPaginatedResponse(data)) {
            return extractPaginatedItems<T>(data) as T[];
        }

        // If a specific data key is provided (e.g., 'bills')
        if (options.dataKey && data && typeof data === 'object' && options.dataKey in data) {
            return data[options.dataKey] as T | T[];
        }

        // Return data as-is
        return data as T | T[];
    }

    // Fallback
    if (options.expectArray) {
        return [] as T[];
    }

    throw new Error(`Invalid API response format: ${JSON.stringify(raw).substring(0, 100)}`);
}
