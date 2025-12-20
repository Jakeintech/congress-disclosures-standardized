import { z } from 'zod';

/**
 * Base pagination schema matching api/lib/response_models.py
 */
export const PaginationSchema = z.object({
    total: z.number().describe('Total number of records available'),
    count: z.number().describe('Number of records in current page'),
    limit: z.number().describe('Maximum records per page'),
    offset: z.number().describe('Offset from start (0-indexed)'),
    has_next: z.boolean().describe('Whether more pages exist'),
    has_prev: z.boolean().describe('Whether previous pages exist'),
    next: z.string().nullable().optional().describe('URL for next page'),
    prev: z.string().nullable().optional().describe('URL for previous page'),
});

/**
 * Base error detail schema
 */
export const ErrorDetailSchema = z.object({
    message: z.string().describe('Human-readable error message'),
    code: z.union([z.number(), z.string()]).describe('Error code'),
    details: z.record(z.string(), z.any()).nullable().optional().describe('Additional error context'),
});

/**
 * Factory for creating API response schemas
 */
export const createAPIResponseSchema = <T extends z.ZodType>(dataSchema: T) =>
    z.object({
        success: z.boolean().describe('Whether the request succeeded'),
        data: dataSchema.describe('Response payload'),
        version: z.string().optional().describe('API version'),
        metadata: z.record(z.string(), z.any()).nullable().optional().describe('Additional metadata'),
        error: ErrorDetailSchema.nullable().optional().describe('Error details'),
    });

/**
 * Factory for creating paginated response item schemas
 */
export const createPaginatedResponseSchema = <T extends z.ZodType>(itemSchema: T) =>
    z.object({
        items: z.array(itemSchema).describe('List of items in current page'),
        pagination: PaginationSchema.describe('Pagination metadata'),
    });

/**
 * Development-only validation wrapper
 * Logs errors but returns data as-is to avoid breaking production
 */
export function validateInDev<T>(
    data: unknown,
    schema: z.ZodSchema<T>,
    context: string = 'API'
): T {
    // In production, we don't want the overhead or the console noise
    if (process.env.NODE_ENV !== 'development') {
        return data as T;
    }

    const result = schema.safeParse(data);
    if (!result.success) {
        console.warn(`[${context}] Validation failed:`, result.error.format());
        // In dev, we might want to see the actual data that failed
        console.dir({ context, originalData: data }, { depth: 5 });
    } else {
        // Optionally log success in high-verbosity mode
        // console.log(`[${context}] Validation passed`);
    }

    // Always return the data, even if validation failed
    return data as T;
}
