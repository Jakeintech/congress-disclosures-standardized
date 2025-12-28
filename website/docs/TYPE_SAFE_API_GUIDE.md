# Type-Safe API Integration Guide

## Problem We Solved

**Bug**: Next.js build failed with `TypeError: .map is not a function` because:
1. API returns: `{ success: true, data: { bills: [...], pagination: {...} } }`
2. Frontend code tried to access: `raw.data` (expecting array)
3. Should have accessed: `raw.data.bills`

**Root Cause**: Lack of type safety and standardized response parsing.

---

## Solution: Type-Safe API Client

### 1. Standardized Response Types

Created [`src/lib/api-types.ts`](file:///Users/jake/Documents/GitHub/congress-disclosures-standardized/website/src/lib/api-types.ts) with:

```typescript
// Standard API wrapper
export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  error?: { message: string; code?: number | string };
  version?: string;
  metadata?: { cache_seconds?: number };
}

// Paginated data structure
export interface PaginatedData<T> {
  [key: string]: T[] | PaginationMeta;
  pagination: PaginationMeta;
}

// Type-safe parser
export function parseAPIResponse<T>(raw: any, options: {
  expectPaginated?: boolean;
  dataKey?: string; // e.g., 'bills', 'trades', 'members'
}): T | T[]
```

### 2. Updated API Calls

**Before** (Bug-prone):
```typescript
const raw = await fetchApi<{ data?: any[] }>(`${url}`);
const data = (Array.isArray(raw) ? raw : raw.data) || [];
return data; // ❌ Assumes data is array, but it's actually data.bills
```

**After** (Type-safe):
```typescript
import { parseAPIResponse } from './api-types';

const raw = await fetchApi(url);
return parseAPIResponse<Bill>(raw, {
  expectPaginated: true,
  dataKey: 'bills' // ✅ Explicitly specifies where the array is
});
```

---

## Best Practices

### ✅ DO: Use Type-Safe Parsers

```typescript
// For paginated endpoints
const bills = await fetchBills({ limit: 10 });
// Internally uses parseAPIResponse with dataKey: 'bills'

// For single-item endpoints
const bill = await fetchBillDetail(billId);
// Returns the data directly
```

### ✅ DO: Specify Expected Structure

```typescript
parseAPIResponse<Bill>(raw, {
  expectPaginated: true,  // Expects { bills: [], pagination: {} }
  dataKey: 'bills'        // Extracts the 'bills' array
})
```

### ❌ DON'T: Make Assumptions

```typescript
// ❌ Bad: Assumes response is array
const data = raw.data || [];

// ❌ Bad: Assumes response structure
const bills = raw.bills;

// ✅ Good: Use parser that handles all cases
const bills = parseAPIResponse<Bill>(raw, { dataKey: 'bills' });
```

---

## Generating Types from OpenAPI Spec

### Setup (Future Enhancement)

```bash
# Install OpenAPI TypeScript generator
npm install -D openapi-typescript

# Generate types
npm run generate-types
# Creates: src/lib/generated/api-schema.ts
```

### Usage

```typescript
import type { components } from './generated/api-schema';

type Bill = components['schemas']['Bill'];
type APIResponse<T> = components['schemas']['APIResponse'] & { data: T };
```

---

## Testing Your API Calls

### 1. Local Testing

```typescript
// Test with real API
const response = await fetch('https://yvpi88rhwl.execute-api.us-east-1.amazonaws.com/v1/congress/bills?limit=1');
const data = await response.json();
console.log(JSON.stringify(data, null, 2));

// Verify structure:
// { success: true, data: { bills: [...], pagination: {...} } }
```

### 2. Add Runtime Validation (Optional)

Use Zod for runtime type checking:

```typescript
import { z } from 'zod';

const BillsResponseSchema = z.object({
  success: z.boolean(),
  data: z.object({
    bills: z.array(z.any()),
    pagination: z.object({
      total: z.number(),
      // ...
    })
  })
});

const raw = await fetchApi(url);
const validated = BillsResponseSchema.parse(raw); // Throws if invalid
```

---

## Checklist for New API Endpoints

When adding a new API endpoint:

- [ ] Check the API response structure (use curl or browser devtools)
- [ ] Define response type in `api-types.ts` (e.g., `MembersResponse`)
- [ ] Use `parseAPIResponse` with correct `dataKey`
- [ ] Add TypeScript types for the data model
- [ ] Test with real API data
- [ ] Update OpenAPI spec if needed

---

## Common Patterns

### Paginated List Endpoints

```typescript
export async function fetchMembers(params: MembersParams = {}): Promise<Member[]> {
  const url = buildURL('/v1/members', params);
  const raw = await fetchApi(url);
  return parseAPIResponse<Member>(raw, {
    expectPaginated: true,
    dataKey: 'members'
  });
}
```

### Single Item Endpoints

```typescript
export async function fetchMember(bioguideId: string): Promise<MemberDetail> {
  const raw = await fetchApi(`/v1/members/${bioguideId}`);
  return parseAPIResponse<MemberDetail>(raw, {
    dataKey: 'member' // Single item, not array
  });
}
```

### Direct Data Endpoints

```typescript
export async function fetchVersion(): Promise<VersionInfo> {
  const raw = await fetchApi('/v1/version');
  return parseAPIResponse<VersionInfo>(raw);
  // No dataKey needed, returns data directly
}
```

---

## Migration Guide

To update existing API calls:

1. **Identify the response structure** (check API docs or test with curl)
2. **Update the function** to use `parseAPIResponse`
3. **Specify the `dataKey`** (e.g., 'bills', 'trades', 'members')
4. **Test** with real data

Example migration:

```diff
export async function fetchTrades(params: TradesParams = {}): Promise<Trade[]> {
  const url = buildURL('/v1/trades', params);
- const raw = await fetchApi<{ data?: any[] }>(url);
- const data = (Array.isArray(raw) ? raw : raw.data) || [];
- return data;
+ const raw = await fetchApi(url);
+ return parseAPIResponse<Trade>(raw, {
+   expectPaginated: true,
+   dataKey: 'trades'
+ });
}
```

---

## Further Reading

- [OpenAPI Specification](../../../openapi.yaml)
- [TypeScript Handbook: Type Guards](https://www.typescriptlang.org/docs/handbook/2/narrowing.html)
- [openapi-typescript Documentation](https://github.com/drwpow/openapi-typescript)
