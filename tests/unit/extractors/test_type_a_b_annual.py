
import pytest
from ingestion.lib.extractors.type_a_b_annual.extractor import TypeABAnnualExtractor

@pytest.fixture
def extractor():
    return TypeABAnnualExtractor()

@pytest.fixture
def sample_annual_text():
    return """
    Camelot, Arthur King  Page 1 of 5
    
    Financial Disclosure Report
    
    Filer Information
    Name: Hon. Arthur King
    Status: Member
    State/District: NY01
    
    Filing Information
    Filing Type: Annual Report
    Filing Year: 2024
    Filing Date: 05/15/2025
    
    Schedule A: Assets and "Unearned" Income
    Asset                                    Owner Value of Asset      Income Type(s)     Income
    Excalibur Fund                           SP    $15,001 - $50,000   Dividends          $201 - $1,000
    Round Table Inc.                         Self  $1,001 - $15,000    None               None
    Camelot Castle                           JT    Over $50,000,000    Rent               $100,001 - $1,000,000
    DESCRIPTION: Royal residence and tourist attraction.
    
    Schedule B: Transactions
    None disclosed.
    
    Schedule C: Earned Income
    Source                        Type            Amount
    Knights of the Round Table    Salary          $174,000
    
    Schedule D: Liabilities
    Owner Creditor   Date Incurred  Type           Amount of Liability
    Self  Iron Bank  Jan 2020       Mortgage       $250,001 - $500,000
    
    Schedule E: Positions
    Position       Name of Organization
    Board Member   Holy Grail Foundation
    
    Schedule F: Agreements
    None disclosed.
    
    Schedule G: Gifts
    None disclosed.
    
    Schedule H: Travel Payments and Reimbursements
    None disclosed.
    
    Schedule I: Payments Made to Charity in Lieu of Honoraria
    None disclosed.
    
    Exclusions of Spouse, Dependent, or Trust Information
    IPO: Did you purchase any shares that were allocated as a part of an Initial Public Offering?  No
    Trusts: Details regarding "Qualified Blind Trusts" approved by the Committee on Ethics and certain other "excepted trusts" need not be disclosed. Have you excluded from this report details of such a trust benefiting you, your spouse, or dependent child?  No
    Exemption: Have you excluded from this report any other assets, "unearned" income, transactions, or liabilities of a spouse or dependent child because they meet all three tests for exemption?  No
    
    Certification and Signature
    I CERTIFY that the statements I have made on the attached Financial Disclosure Report are true, complete, and correct to the best of my knowledge and belief.
    Digitally Signed: Hon. Arthur King , 05/15/2025
    """

def test_extract_filer_info(extractor, sample_annual_text):
    data = extractor.extract_from_text(sample_annual_text)
    info = data["filer_info"]
    
    assert info["full_name"] == "Arthur King"
    assert info["filer_type"] == "Member"
    assert info["state_district"] == "NY01"
    assert info["year"] == 2024
    assert info["filing_type"] == "A"

def test_extract_assets(extractor, sample_annual_text):
    data = extractor.extract_from_text(sample_annual_text)
    assets = data["schedule_a"]
    
    assert len(assets) == 3
    
    # Check Excalibur Fund
    a1 = assets[0]
    assert "Excalibur Fund" in a1["asset_name"]
    assert a1["owner_code"] == "SP"
    assert a1["value_low"] == 15001
    assert a1["income_type"] == "Dividends"
    
    # Check Camelot Castle
    a3 = assets[2]
    assert "Camelot Castle" in a3["asset_name"]
    assert a3["value_low"] == 50000001
    assert a3["income_type"] == "Rent"
    # description is not captured? 
    # _extract_assets_and_income regex doesn't seem to look for DESCRIPTION: lines explicitly, 
    # but maybe _parse_asset_entry handles it if it's part of the buffer?
    
def test_extract_liabilities(extractor, sample_annual_text):
    data = extractor.extract_from_text(sample_annual_text)
    liabs = data["schedule_d"]
    assert len(liabs) == 1
    assert liabs[0]["creditor_name"] == "Iron Bank"
    assert liabs[0]["owner_code"] == "Self"

def test_extract_positions(extractor, sample_annual_text):
    data = extractor.extract_from_text(sample_annual_text)
    positions = data["schedule_e"]
    assert len(positions) == 1
    assert "Board Member" in positions[0]["position_title"]

def test_certification(extractor, sample_annual_text):
    data = extractor.extract_from_text(sample_annual_text)
    cert = data["certification"]
    assert cert["filer_certified"] is True
    assert cert["filer_signature"] == "Hon. Arthur King"
    assert cert["filer_signature_date"] == "2025-05-15" # depending on extract_date format
