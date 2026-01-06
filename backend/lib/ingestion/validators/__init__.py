"""
Base Validator class.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any

class Validator(ABC):
    """Base class for all validators."""
    
    def __init__(self):
        self.issues = []
        
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validate the data and return a list of issues.
        
        Args:
            data: The data to validate (e.g., extracted JSON)
            
        Returns:
            List of issues, where each issue is a dict with:
            - code: Error code
            - message: Description
            - severity: 'error' or 'warning'
            - field: Field name (optional)
        """
        pass
