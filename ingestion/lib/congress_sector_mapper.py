"""
Congress Sector Mapper - Maps policy areas to financial sectors.

Maps Congress.gov bill policy areas and subjects to standard financial sectors
(GICS-style) for FD-Congress correlation analysis.
"""

from typing import List, Optional

# Policy Area → Financial Sector mapping
# Based on Congress.gov policy area taxonomy mapped to GICS sectors
POLICY_AREA_TO_SECTOR = {
    # Healthcare
    "health": "Healthcare",
    "health care": "Healthcare", 
    "medicare": "Healthcare",
    "medicaid": "Healthcare",
    "drugs": "Healthcare",
    "pharmaceuticals": "Healthcare",
    
    # Technology
    "science, technology, communications": "Technology",
    "science and technology": "Technology",
    "technology": "Technology",
    "telecommunications": "Technology",
    "computers and information technology": "Technology",
    "internet": "Technology",
    "cybersecurity": "Technology",
    
    # Energy
    "energy": "Energy",
    "oil and gas": "Energy",
    "nuclear energy": "Energy",
    "renewable energy": "Energy",
    "electricity": "Energy",
    
    # Financials
    "finance and financial sector": "Financials",
    "banking and financial services": "Financials",
    "banks and banking": "Financials",
    "securities": "Financials",
    "insurance": "Financials",
    "credit": "Financials",
    
    # Defense
    "armed forces and national security": "Defense",
    "defense": "Defense",
    "military": "Defense",
    "national defense": "Defense",
    "veterans": "Defense",
    
    # Industrials
    "transportation and public works": "Industrials",
    "transportation": "Industrials",
    "aviation": "Industrials",
    "railroads": "Industrials",
    "manufacturing": "Industrials",
    "infrastructure": "Industrials",
    
    # Materials
    "environmental protection": "Materials",
    "water resources development": "Materials",
    "mining": "Materials",
    "metals": "Materials",
    
    # Consumer
    "commerce": "Consumer",
    "consumer protection": "Consumer",
    "retail": "Consumer",
    "agriculture and food": "Consumer",
    "housing": "Consumer",
    
    # Real Estate
    "real estate": "Real Estate",
    "housing and community development": "Real Estate",
    
    # Utilities
    "utilities": "Utilities",
    "public utilities": "Utilities",
    
    # Communications
    "communications": "Communications",
    "media": "Communications",
    "broadcasting": "Communications",
    
    # Education
    "education": "Education",
    "higher education": "Education",
    
    # Government/Other
    "government operations and politics": "Government",
    "congress": "Government",
    "public lands and natural resources": "Government",
    "international affairs": "Government",
    "foreign trade and international finance": "Trade",
    "taxation": "Government",
    "economics and public finance": "Government",
    "social welfare": "Government",
    "crime and law enforcement": "Government",
    "civil rights and liberties, minority issues": "Government",
    "immigration": "Government",
    "labor and employment": "Government",
    "families": "Government",
    "native americans": "Government",
    "law": "Government",
    "emergency management": "Government",
    "sports and recreation": "Consumer",
    "arts, culture, religion": "Consumer",
    "animals": "Consumer",
}


def map_policy_area_to_sector(policy_area: Optional[str]) -> str:
    """
    Map a Congress.gov policy area to a financial sector.
    
    Args:
        policy_area: The policy area string from Congress.gov (e.g., "Health")
    
    Returns:
        The corresponding financial sector (e.g., "Healthcare") or "General" if unmapped
    """
    if not policy_area:
        return "General"
    
    # Normalize: lowercase and strip
    normalized = policy_area.lower().strip()
    
    # Direct lookup
    if normalized in POLICY_AREA_TO_SECTOR:
        return POLICY_AREA_TO_SECTOR[normalized]
    
    # Partial match (check if any key is contained in the policy area)
    for key, sector in POLICY_AREA_TO_SECTOR.items():
        if key in normalized:
            return sector
    
    return "General"


def map_subjects_to_sectors(subjects: Optional[List[str]]) -> List[str]:
    """
    Map a list of Congress.gov subjects to unique financial sectors.
    
    Args:
        subjects: List of subject strings
    
    Returns:
        Unique list of financial sectors
    """
    if not subjects:
        return ["General"]
    
    sectors = set()
    for subject in subjects:
        sector = map_policy_area_to_sector(subject)
        sectors.add(sector)
    
    # Remove "General" if we have more specific sectors
    if len(sectors) > 1 and "General" in sectors:
        sectors.discard("General")
    
    return sorted(list(sectors))


# Standard sectors for reference
FINANCIAL_SECTORS = [
    "Healthcare",
    "Technology", 
    "Energy",
    "Financials",
    "Defense",
    "Industrials",
    "Materials",
    "Consumer",
    "Real Estate",
    "Utilities",
    "Communications",
    "Education",
    "Government",
    "Trade",
    "General",
]


if __name__ == "__main__":
    # Test the mapper
    test_cases = [
        "Health",
        "Science, Technology, Communications",
        "Armed Forces and National Security",
        "Finance and Financial Sector",
        "Energy",
        "Unknown Policy Area",
        None,
    ]
    
    print("Testing congress_sector_mapper:")
    for policy_area in test_cases:
        sector = map_policy_area_to_sector(policy_area)
        print(f"  '{policy_area}' → '{sector}'")
