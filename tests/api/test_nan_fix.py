import json
import math
import sys
import os

# Add api directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.lib.response_formatter import NaNToNoneEncoder, success_response

def test_nan_serialization():
    data = {
        "ticker": "AAPL",
        "volume": float('nan'),
        "price": 150.0,
        "details": {
            "inf_value": float('inf'),
            "neg_inf": float('-inf'),
            "nested": [1.0, float('nan'), 3.0]
        }
    }
    
    # 1. Test Encoder directly
    encoded = json.dumps(data, cls=NaNToNoneEncoder)
    print(f"Direct Encoder Output: {encoded}")
    assert 'null' in encoded
    assert 'NaN' not in encoded
    
    # 2. Test success_response
    response = success_response(data)
    print(f"Success Response Body: {response['body']}")
    assert 'null' in response['body']
    assert 'NaN' not in response['body']
    
    print("Test passed!")

if __name__ == "__main__":
    test_nan_serialization()
