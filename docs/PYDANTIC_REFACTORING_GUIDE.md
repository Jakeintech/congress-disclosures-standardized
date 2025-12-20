# Pydantic Refactoring Guide for Lambda Handlers

This guide shows how to refactor Lambda handlers to use Pydantic models for type-safe responses.

## Benefits

- **OpenAPI Auto-Generation**: Pydantic models can be introspected to generate OpenAPI specs
- **Type Safety**: Catch type errors at runtime before they reach clients
- **Documentation**: Self-documenting code with descriptions and examples
- **Validation**: Automatic validation of response data
- **TypeScript Generation**: OpenAPI specs generate TypeScript types for frontend

## Prerequisites

1. Pydantic models defined in `api/lib/response_models.py`
2. `response_formatter.py` updated to support Pydantic models (✅ done)
3. Pydantic installed in Lambda layer (✅ added to requirements.txt)

## Pattern: Simple Response

### Before (Dict-based)

```python
# api/lambdas/get_version/handler.py (OLD)
from api.lib import success_response, error_response

def handler(event, context):
    try:
        # Build response as dict
        response = {
            "version": "v20251220-33a4c83",
            "git": {
                "commit": "33a4c83...",
                "branch": "main"
            },
            "status": "healthy"
        }

        return success_response(response)
    except Exception as e:
        return error_response(str(e), 500)
```

**Issues:**
- No type safety
- No validation
- Cannot auto-generate OpenAPI spec
- Easy to make mistakes with field names/types

### After (Pydantic-based)

```python
# api/lambdas/get_version/handler.py (NEW)
from api.lib import success_response, error_response
from api.lib.response_models import (
    VersionData,
    GitInfo,
    BuildInfo,
    RuntimeInfo
)

def handler(event, context):
    try:
        # Build type-safe Pydantic models
        git_info = GitInfo(
            commit="33a4c83...",
            commit_short="33a4c83",
            branch="main",
            dirty=False
        )

        build_info = BuildInfo(
            timestamp="2025-12-20T10:30:00Z",
            date="2025-12-20"
        )

        runtime_info = RuntimeInfo(
            function_name=context.function_name,
            function_version=context.function_version,
            aws_request_id=context.aws_request_id,
            memory_limit_mb=context.memory_limit_in_mb
        )

        version_response = VersionData(
            version="v20251220-33a4c83",
            git=git_info,
            build=build_info,
            api_version="v1",
            runtime=runtime_info,
            status="healthy"
        )

        # Convert to dict before passing to response_formatter
        return success_response(version_response.model_dump())

    except Exception as e:
        return error_response(str(e), 500)
```

**Benefits:**
- Type checking catches errors (e.g., typo in field name)
- IDE autocomplete for all fields
- Pydantic validates data types automatically
- Can generate OpenAPI spec from models
- Self-documenting with field descriptions

## Pattern: Paginated Response

### Before (Dict-based)

```python
# api/lambdas/get_members/handler.py (OLD)
from api.lib import success_response

def handler(event, context):
    # Query members from DuckDB
    members = query_members(limit=20, offset=0)
    total = count_members()

    # Build pagination manually
    response = {
        "members": members,
        "pagination": {
            "total": total,
            "count": len(members),
            "limit": 20,
            "offset": 0,
            "has_next": total > 20,
            "has_prev": False
        }
    }

    return success_response(response)
```

### After (Pydantic-based)

```python
# api/lambdas/get_members/handler.py (NEW)
from api.lib import success_response
from api.lib.response_models import (
    Member,
    PaginatedResponse,
    PaginationMetadata
)

def handler(event, context):
    # Query members from DuckDB
    members_data = query_members(limit=20, offset=0)
    total = count_members()

    # Build type-safe Member objects
    members = [
        Member(
            bioguide_id=row['bioguide_id'],
            name=row['name'],
            party=row['party'],
            state=row['state'],
            chamber=row['chamber'],
            district=row.get('district'),
            total_trades=row.get('total_trades', 0)
        )
        for row in members_data
    ]

    # Build pagination metadata
    pagination = PaginationMetadata(
        total=total,
        count=len(members),
        limit=20,
        offset=0,
        has_next=total > 20,
        has_prev=False,
        next="/v1/members?limit=20&offset=20" if total > 20 else None,
        prev=None
    )

    # Build paginated response
    paginated = PaginatedResponse(
        items=members,
        pagination=pagination
    )

    return success_response(paginated.model_dump())
```

## Pattern: List Response (Non-Paginated)

### Before

```python
from api.lib import success_response

def handler(event, context):
    stocks = query_trending_stocks(limit=10)
    return success_response({"stocks": stocks})
```

### After

```python
from api.lib import success_response
from api.lib.response_models import TrendingStock

def handler(event, context):
    stocks_data = query_trending_stocks(limit=10)

    stocks = [
        TrendingStock(
            ticker=row['ticker'],
            name=row['name'],
            trade_count_7d=row['trade_count_7d'],
            trade_count_30d=row['trade_count_30d'],
            purchase_count=row['purchase_count'],
            sale_count=row['sale_count'],
            net_sentiment=row.get('net_sentiment')
        )
        for row in stocks_data
    ]

    return success_response({"stocks": [s.model_dump() for s in stocks]})
```

## Pattern: Complex Nested Response

For handlers that return complex nested data (e.g., bill detail with cosponsors, actions, etc.):

```python
from api.lib import success_response
from api.lib.response_models import Bill, Member

def handler(event, context):
    bill_data = query_bill_detail(bill_id)

    # Build sponsor model
    sponsor = Member(
        bioguide_id=bill_data['sponsor_bioguide_id'],
        name=bill_data['sponsor_name'],
        party=bill_data['sponsor_party'],
        state=bill_data['sponsor_state'],
        chamber='house'
    )

    # Build bill model
    bill = Bill(
        bill_id=bill_data['bill_id'],
        congress=bill_data['congress'],
        bill_type=bill_data['bill_type'],
        bill_number=bill_data['bill_number'],
        title=bill_data['title'],
        introduced_date=bill_data['introduced_date'],
        sponsor_bioguide_id=sponsor.bioguide_id,
        sponsor_name=sponsor.name,
        sponsor_party=sponsor.party,
        sponsor_state=sponsor.state,
        cosponsors_count=bill_data['cosponsors_count']
    )

    return success_response(bill.model_dump())
```

## Creating New Pydantic Models

When you need a new model that doesn't exist in `response_models.py`:

### 1. Define the Model

```python
# In api/lib/response_models.py

class YourNewModel(BaseModel):
    """Description of what this model represents"""

    field_name: str = Field(..., description="Field description")
    optional_field: Optional[int] = Field(None, description="Optional field")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field_name": "example value",
                "optional_field": 123
            }
        }
    )
```

### 2. Add Type Alias (if needed)

```python
# At the bottom of response_models.py

YourNewModelResponse = APIResponse[YourNewModel]
```

### 3. Use in Handler

```python
from api.lib.response_models import YourNewModel

def handler(event, context):
    model = YourNewModel(field_name="value")
    return success_response(model.model_dump())
```

## Common Patterns & Best Practices

### 1. Always use `.model_dump()` before passing to `success_response()`

```python
# ✅ CORRECT
model = Member(bioguide_id="C001117", name="Crockett, Jasmine", ...)
return success_response(model.model_dump())

# ❌ WRONG (response_formatter will auto-convert, but prefer explicit)
return success_response(model)
```

### 2. Handle Optional Fields

```python
# Use .get() for optional fields from database
Member(
    bioguide_id=row['bioguide_id'],  # Required
    name=row['name'],                # Required
    district=row.get('district'),    # Optional - None if not present
    total_trades=row.get('total_trades', 0)  # Optional with default
)
```

### 3. Validate Data Early

```python
try:
    member = Member(**row_data)  # Pydantic validates all fields
except ValidationError as e:
    logger.error(f"Invalid member data: {e}")
    return error_response("Invalid data", 500, details=str(e))
```

### 4. Use Enums for Limited Values

```python
from api.lib.response_models import Party, Chamber

member = Member(
    party=Party.DEMOCRAT,  # Type-safe, can't pass invalid value
    chamber=Chamber.HOUSE
)
```

### 5. Reuse Common Models

Don't duplicate models - reuse existing ones:

```python
# ✅ CORRECT - Reuse Member model
from api.lib.response_models import Member

sponsor = Member(bioguide_id="...", name="...", ...)

# ❌ WRONG - Don't create duplicate models
class Sponsor(BaseModel):  # DON'T DO THIS
    bioguide_id: str
    name: str
```

## Refactoring Checklist

When refactoring a handler:

- [ ] Import Pydantic models from `api.lib.response_models`
- [ ] Replace dict construction with Pydantic model construction
- [ ] Handle optional fields with `.get()` or default values
- [ ] Use `.model_dump()` before passing to `success_response()`
- [ ] Test the handler locally or in dev environment
- [ ] Verify response structure matches previous behavior
- [ ] Update any handler-specific tests

## Testing Refactored Handlers

### Unit Test Example

```python
import pytest
from api.lambdas.get_version.handler import handler

def test_version_handler():
    """Test that version handler returns valid Pydantic model"""
    class MockContext:
        function_name = "get_version"
        function_version = "$LATEST"
        aws_request_id = "test-123"
        memory_limit_in_mb = 512

    response = handler({}, MockContext())

    assert response['statusCode'] == 200

    body = json.loads(response['body'])
    assert body['success'] is True
    assert 'version' in body['data']
    assert 'git' in body['data']
    assert 'build' in body['data']
    assert 'runtime' in body['data']
```

### Integration Test with OpenAPI Validation

After Phase 2 (OpenAPI generation), you can validate responses:

```python
from openapi_spec_validator import validate_spec
import yaml

def test_handler_matches_openapi():
    """Ensure handler response matches OpenAPI spec"""
    response = handler({}, context)
    body = json.loads(response['body'])

    # Load OpenAPI spec
    with open('openapi.yaml') as f:
        spec = yaml.safe_load(f)

    # Validate response matches schema
    assert_matches_schema(body, spec['paths']['/v1/version']['get']['responses']['200'])
```

## Migration Strategy

Given 127 handlers, refactor in phases:

### Phase 1: System/Utility (5 handlers) ✅
- ✅ `get_version` (example complete)
- `get_summary`
- `search`
- `get_aws_costs`
- `list_s3_objects`

### Phase 2: High-Traffic Endpoints (20 handlers)
- Members endpoints (8 handlers)
- Bills endpoints (8 handlers)
- Trading/Stocks (4 handlers)

### Phase 3: Analytics & Insights (10 handlers)
- Dashboard, trending stocks, top traders, etc.

### Phase 4: Remaining Endpoints (92 handlers)
- Batch refactor using automated tools or agents

## Troubleshooting

### Issue: `ValidationError` when constructing model

**Cause:** Missing required field or wrong data type

**Fix:** Check the model definition and ensure all required fields are provided

```python
# ERROR: Missing 'name' field
member = Member(bioguide_id="C001117")  # ❌ ValidationError

# FIX: Provide all required fields
member = Member(
    bioguide_id="C001117",
    name="Crockett, Jasmine",  # ✅
    party="D",
    state="TX",
    chamber="house"
)
```

### Issue: `TypeError: Object of type Member is not JSON serializable`

**Cause:** Forgot to call `.model_dump()`

**Fix:**

```python
# ERROR
return success_response(member)  # ❌

# FIX
return success_response(member.model_dump())  # ✅
```

### Issue: Response structure changed after refactoring

**Cause:** Pydantic excludes `None` values by default

**Fix:** Use `model_dump(exclude_none=False)` if you need to preserve `null` fields

```python
return success_response(model.model_dump(exclude_none=False))
```

## Next Steps

After refactoring handlers:

1. **Phase 2**: Generate OpenAPI spec from Pydantic models
2. **Phase 3**: Generate TypeScript types from OpenAPI
3. **Phase 4**: Create Zod schemas for frontend validation
4. **Phase 5**: Integrate types into frontend API calls

See `docs/LAMBDA_RESPONSE_AUDIT.md` for full handler inventory.
