import os
import json
import yaml
import importlib.util
import sys
from typing import Dict, Any, List, Type, Optional
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema

# Add the project root to sys.path to allow imports from api.lib
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

def get_pydantic_models() -> Dict[str, Type[BaseModel]]:
    """
    Import response_models.py and extract all Pydantic models.
    """
    from api.lib import response_models
    
    models = {}
    for name in dir(response_models):
        item = getattr(response_models, name)
        if isinstance(item, type) and issubclass(item, BaseModel) and item is not BaseModel:
            models[name] = item
    return models

def get_lambda_handlers_metadata() -> List[Dict[str, Any]]:
    """
    Load lambda handler metadata from route_mappings.json configuration file.
    """
    route_mappings_path = os.path.join(PROJECT_ROOT, "api/route_mappings.json")

    if not os.path.exists(route_mappings_path):
        print(f"Warning: route_mappings.json not found at {route_mappings_path}", file=sys.stderr)
        return []

    with open(route_mappings_path, 'r') as f:
        mappings = json.load(f)

    # Convert dict to list of handler metadata
    handlers = []
    for handler_name, config in mappings.items():
        handler_meta = {
            "handler_name": handler_name,
            **config
        }
        handlers.append(handler_meta)

    return handlers

def generate_openapi_spec():
    """
    Generate OpenAPI 3.1.0 specification from Pydantic models and handler metadata.
    """
    models = get_pydantic_models()
    handlers = get_lambda_handlers_metadata()
    
    # Generate JSON schemas for all models
    # We use a dummy model to collect all schemas in one go
    class AllModels(BaseModel):
        pass
    
    # This is a common trick to get all referenced schemas
    # For simplicity, we'll just gather them manually here or use models_json_schema
    
    spec = {
        "openapi": "3.1.0",
        "info": {
            "title": "Congressional Trading API",
            "description": "API for accessing standardized congressional financial disclosures and legislative data.",
            "version": "1.0.0"
        },
        "servers": [
            {"url": "https://api.congress-disclosures.com", "description": "Production API"},
            {"url": "http://localhost:3000", "description": "Local development"}
        ],
        "paths": {},
        "components": {
            "schemas": {}
        }
    }
    
    # Add paths
    for h in handlers:
        path = h["path"]
        method = h["method"]
        
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        
        spec["paths"][path][method] = {
            "summary": h["summary"],
            "tags": h.get("tags", []),
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": f"#/components/schemas/{h['response_model']}"
                            }
                        }
                    }
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "404": {"$ref": "#/components/responses/NotFound"},
                "500": {"$ref": "#/components/responses/InternalError"}
            }
        }
        
        if "parameters" in h:
            spec["paths"][path][method]["parameters"] = h["parameters"]

    # Add common responses
    spec["components"]["responses"] = {
        "BadRequest": {
            "description": "Bad Request",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}
        },
        "NotFound": {
            "description": "Not Found",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}
        },
        "InternalError": {
            "description": "Internal Server Error",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}
        }
    }

    # Generate schemas for all components
    # We'll use pydantic's built-in schema generation
    # Note: response_models.py has aliases like MemberResponse = APIResponse[Member]
    # We need to ensure these are captured. 
    
    # For this script, we'll just iterate over all models found
    model_list = list(models.values())
    _, top_level_schema = models_json_schema([(m, 'serialization') for m in model_list], ref_template="#/components/schemas/{model}")
    
    spec["components"]["schemas"] = top_level_schema.get("$defs", top_level_schema)
    # If using $defs, move them to schemas
    if "$defs" in spec["components"]["schemas"]:
        spec["components"]["schemas"] = spec["components"]["schemas"]["$defs"]

    # Final cleanup of schemas
    # Pydantic might add some extra fields we don't want in OpenAPI
    
    return spec

if __name__ == "__main__":
    spec = generate_openapi_spec()
    
    # Save as YAML
    with open(os.path.join(PROJECT_ROOT, "docs/openapi.yaml"), "w") as f:
        yaml.dump(spec, f, sort_keys=False, default_flow_style=False)
    
    # Also save as JSON for convenience
    with open(os.path.join(PROJECT_ROOT, "docs/openapi.json"), "w") as f:
        json.dump(spec, f, indent=2)
    
    print(f"Generated OpenAPI spec with {len(spec['paths'])} endpoints and {len(spec['components']['schemas'])} schemas.")
