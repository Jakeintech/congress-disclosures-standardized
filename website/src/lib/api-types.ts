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
    const context = options.context || 'API';
    console.log(`[parseAPIResponse][${context}] Starting parse`, {
        expectPaginated: options.expectPaginated,
        expectArray: options.expectArray,
        dataKey: options.dataKey,
        rawType: typeof raw,
        isArray: Array.isArray(raw),
        hasData: raw && 'data' in raw,
        rawKeys: raw && typeof raw === 'object' ? Object.keys(raw) : []
    });

    // 1. Initial Data Extraction
    let data: any;
    // Handle direct array responses (legacy)
    if (Array.isArray(raw)) {
        console.log(`[parseAPIResponse][${context}] Raw is direct array, returning`, raw.length, 'items');
        return raw as T[];
    }

    // Standard API response wrapper
    if (raw && typeof raw === 'object' && 'data' in raw) {
        data = raw.data;
        console.log(`[parseAPIResponse][${context}] Extracted raw.data`, {
            dataType: typeof data,
            isArray: Array.isArray(data),
            dataKeys: data && typeof data === 'object' ? Object.keys(data) : [],
            hasPagination: data && 'pagination' in data,
            hasItems: data && 'items' in data
        });

        // If a specific data key is provided (e.g., 'bills') inside data
        if (options.dataKey && data && typeof data === 'object' && options.dataKey in data) {
            data = data[options.dataKey];
            console.log(`[parseAPIResponse][${context}] Extracted dataKey=${options.dataKey}`, Array.isArray(data) ? data.length : typeof data);
        }
        // If expecting paginated response and it looks paginated
        else if (options.expectPaginated && isPaginatedResponse(data)) {
            console.log(`[parseAPIResponse][${context}] Detected paginated response, extracting items`);
            const extracted = extractPaginatedItems<T>(data);
            console.log(`[parseAPIResponse][${context}] Extracted ${extracted.length} items from paginated response`);
            data = extracted;
        }
    } else {
        console.log(`[parseAPIResponse][${context}] No standard wrapper, using raw data directly`);
        data = raw;
    }

    // 2. Fallback for arrays
    if (!data && options.expectArray) {
        console.log(`[parseAPIResponse][${context}] Data is falsy, returning empty array (expectArray=true)`);
        data = [];
    }

    // 3. Validation (Dev only)
    if (options.schema) {
        validateInDev(data, options.schema, context);
    }

    console.log(`[parseAPIResponse][${context}] Final result`, {
        isArray: Array.isArray(data),
        length: Array.isArray(data) ? data.length : undefined,
        type: typeof data
    });

    return data as T | T[];
}
