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
