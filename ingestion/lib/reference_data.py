"""
Reference Data for House Financial Disclosures.
Source: https://fd.house.gov/reference/asset-type-codes.aspx
"""

ASSET_TYPE_CODES = {
    "5P": "529 Prepaid Tuition",
    "5S": "529 Savings Plan",
    "AB": "Asset-Backed Security",
    "BA": "Bank Accounts, Money Market Accounts, and CDs",
    "bond": "Corporate Bond",
    "bonds": "Corporate Bond",
    "CB": "Corporate Bond",
    "CO": "Collectibles",
    "CS": "Corporate Securities (Stock)",
    "CT": "Crypto",
    "DC": "Deferred Compensation",
    "DO": "Debts Owed to the Filer",
    "DV": "Derivatives",
    "EQ": "Equity",
    "EL": "Equity Index-Linked Note",
    "EU": "Exchange Traded Funds/Notes",
    "E": "Exchange Traded Funds/Notes", # Common abbreviation
    "F": "Farm",
    "FN": "Foreign Currency",
    "GS": "Government Securities",
    "GT": "Gift",
    "HE": "Hedge Funds",
    "IH": "Investment Fund (Hedge, Private Equity, etc.)",
    "IP": "Intellectual Property",
    "IR": "IRA",
    "LC": "Limited Liability Company (LLC)",
    "LP": "Limited Partnership (LP)",
    "MF": "Mutual Funds",
    "MA": "Managed Account",
    "MO": "Municipal Security",
    "NG": "Non-Publicly Traded Securities",
    "NP": "Note Payable",
    "OA": "Other Assets",
    "OP": "Option",
    "OT": "Other",
    "OI": "Ownership Interest",
    "OL": "Ownership Interest (LLC)",
    "OP": "Ownership Interest (Partnership)",
    "OS": "Ownership Interest (S-Corp)",
    "PE": "Private Equity",
    "PS": "Publicly Traded Securities",
    "RE": "Real Estate",
    "RP": "Real Property",
    "RS": "Restricted Stock",
    "S": "Stock",
    "ST": "Stock",
    "SA": "Savings Accounts",
    "SB": "Savings Bond",
    "SC": "S-Corp",
    "SF": "State/Municipal Security",
    "TR": "Trust",
    "UST": "U.S. Treasury Securities",
    "VI": "Variable Insurance",
    "VP": "Variable Annuity",
    "WA": "Warrant",
    "WE": "Waste/Environment",
    "WU": "Whole Life Insurance"
}

FILING_TYPES = {
    "P": "Periodic Transaction Report",
    "A": "Annual Financial Disclosure",
    "B": "New Filer Report",
    "C": "Candidate Report",
    "T": "Termination Report",
    "X": "Extension Request",
    "D": "Campaign Notice",
    "W": "Withdrawal Notice",
    "E": "Electronic Copy",
    "N": "New Filer Notification",
    "G": "Gift Travel Report",
    "U": "Unknown"
}

def get_asset_type_description(code: str) -> str:
    """Get description for asset type code."""
    if not code:
        return None
    return ASSET_TYPE_CODES.get(code.upper(), "Unknown")


# Fallback data for when API enrichment fails
# This ensures we at least have party data for prominent members in the graph
MEMBER_PARTY_MAP = {
    # Leadership & Prominent (Democrat)
    "nancy pelosi": "Democrat",
    "hakeem jeffries": "Democrat",
    "katherine clark": "Democrat",
    "pete aguilar": "Democrat",
    "ro khanna": "Democrat",
    "alexandria ocasio-cortez": "Democrat",
    "rashida tlaib": "Democrat",
    "ilhan omar": "Democrat",
    "adam schiff": "Democrat",
    "jamie raskin": "Democrat",
    "josh gottheimer": "Democrat",
    "susie lee": "Democrat",
    "earl blumenauer": "Democrat",
    "maxine waters": "Democrat",
    "rosa delauro": "Democrat",
    "richard neal": "Democrat",
    "jim clyburn": "Democrat",
    "steny hoyer": "Democrat",
    
    # Leadership & Prominent (Republican)
    "mike johnson": "Republican",
    "steve scalise": "Republican",
    "tom emmer": "Republican",
    "elise stefanik": "Republican",
    "marjorie taylor greene": "Republican",
    "matt gaetz": "Republican",
    "jim jordan": "Republican",
    "james comer": "Republican",
    "virginia foxx": "Republican",
    "michael mccaul": "Republican",
    "dan crenshaw": "Republican",
    "kevin hern": "Republican",
    "tommy tuberville": "Republican", # Senate but often in data
    "mark green": "Republican",
    "pete sessions": "Republican",
    "chip roy": "Republican",
    "lauren boebert": "Republican",
    "thomas massie": "Republican",
    "patrick mchenry": "Republican",
    "french hill": "Republican"
}

def normalize_member_name(first: str, last: str) -> str:
    """Normalize member name for lookup."""
    return f"{first} {last}".lower().strip()

def get_member_party(first: str, last: str) -> str:
    """
    Get party from static map.
    
    Args:
        first: First name
        last: Last name
        
    Returns:
        'Democrat', 'Republican', or None
    """
    name = normalize_member_name(first, last)
    return MEMBER_PARTY_MAP.get(name)
