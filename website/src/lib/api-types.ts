/**
 * OpenAPI Response Types
 * 
 * Standard response wrapper for all API endpoints
 */

import type { Bill } from '../types/api';
import { z } from 'zod';
import { validateInDev } from './schemas/base';
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
    // Prioritize 'items' key, then fallback to other arrays
    if (Array.isArray(response.items)) {
        return response.items as T[];
    }

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
        schema?: z.ZodSchema<T>;
        context?: string;
    } = {}
): T | T[] {
    // 1. Initial Data Extraction
    let data: any;
    // Handle direct array responses (legacy)
    if (Array.isArray(raw)) {
        return raw as T[];
    }

    // Standard API response wrapper
    if (raw && typeof raw === 'object' && 'data' in raw) {
        data = raw.data;

        // If a specific data key is provided (e.g., 'bills') inside data
        if (options.dataKey && data && typeof data === 'object' && options.dataKey in data) {
            data = data[options.dataKey];
        }
        // If expecting paginated response and it looks paginated
        else if (options.expectPaginated && isPaginatedResponse(data)) {
            data = extractPaginatedItems<T>(data);
        }
    } else {
        data = raw;
    }

    // 2. Fallback for arrays
    if (!data && options.expectArray) {
        data = [];
    }

    // 3. Validation (Dev only)
    if (options.schema) {
        validateInDev(data, options.schema, options.context || 'API');
    }

    return data as T | T[];
}
