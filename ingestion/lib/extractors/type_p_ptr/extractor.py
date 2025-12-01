"""PTR (Periodic Transaction Report) extractor.

Extracts structured data from PTR forms into house_fd_ptr.json schema.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from ..base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class PTRExtractor(BaseExtractor):
    """Extract structured data from Periodic Transaction Reports."""

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract PTR data from text.

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata from OCR or direct extraction

        Returns:
            Structured data matching house_fd_ptr.json schema
        """
        pdf_properties = pdf_properties or {}
        logger.info("Extracting PTR data from text")

        # Clean text of null bytes and excessive whitespace
        text = text.replace('\x00', '')

        # Extract each section
        filer_info = self._extract_filer_info(text)
        ipo_allocated = self._extract_ipo_question(text)
        transactions = self._extract_transactions(text)
        certification = self._extract_certification(text)

        # Calculate field-level confidence and data completeness
        field_confidence = self._calculate_field_confidence(filer_info, transactions, certification)
        data_completeness = self._calculate_data_completeness(filer_info, transactions, certification)
        overall_confidence = sum(field_confidence.values()) / len(field_confidence) if field_confidence else 0.5

        # Build structured output
        result = {
            "filer_info": filer_info,
            "report_type": {
                "is_initial": True,  # TODO: detect from text
                "is_amendment": False,
                "date_of_report_being_amended": None
            },
            "ipo_shares_allocated": ipo_allocated,
            "transactions": transactions,
            "filer_notes": [],  # TODO: extract notes if present
            "certification": certification,
            "filing_metadata": {
                "transaction_count": len(transactions)
            },
            "extraction_metadata": self.create_extraction_metadata(
                confidence=overall_confidence,
                method="regex",
                field_confidence=field_confidence,
                data_completeness=data_completeness
            )
        }

        return result

    def _extract_filer_info(self, text: str) -> Dict[str, Any]:
        """Extract filer information from header."""
        from ..type_a_b_annual.field_extractors import normalize_date_format
        
        filer_info = {
            "full_name": None,
            "filer_type": None,
            "state": None,
            "district": None,
            "year": None,
        }

        # Extract name - try multiple patterns
        name_patterns = [
            r'Name:\s*(.+?)(?:\n|Status:|State:)',
            r'Filer(?:\s+Name)?:\s*(.+?)(?:\n|Status:|State:)',
            r'(?:^|\n)([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)\s*(?:\n|Status:)',
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if name_match:
                name = name_match.group(1).strip()
                # Clean up name (remove excessive whitespace, "Hon.", etc.)
                name = re.sub(r'\s+', ' ', name)
                name = re.sub(r'^(?:Hon\.|The Honorable)\s+', '', name, flags=re.IGNORECASE)
                filer_info["full_name"] = name
                break

        # Extract status/type
        status_match = re.search(r'Status:\s*(Member|Officer\s+or\s+Employee|Employee|Congressional\s+Candidate|Candidate|Former\s+Member)', text, re.IGNORECASE)
        if status_match:
            filer_info["filer_type"] = status_match.group(1).strip()

        # Extract state/district
        state_dist_patterns = [
            r'State(?:/|\s+)District:\s*([A-Z]{2})[\s\-]*(\d{1,2})',
            r'State:\s*([A-Z]{2}).*?District:\s*(\d{1,2})',
            r'\b([A-Z]{2})[\s\-]*(\d{1,2})\b',
        ]
        
        for pattern in state_dist_patterns:
            state_dist_match = re.search(pattern, text)
            if state_dist_match:
                state = state_dist_match.group(1)
                district = state_dist_match.group(2)
                filer_info["state"] = state
                filer_info["district"] = district
                break
        
        # Extract calendar year (often in header or footer)
        year_match = re.search(r'\b(20\d{2})\b', text)
        if year_match:
            filer_info["year"] = int(year_match.group(1))

        logger.debug(f"Extracted filer info: {filer_info}")
        return filer_info

    def _extract_ipo_question(self, text: str) -> bool:
        """Extract IPO shares allocated question response."""
        # Look for IPO section
        ipo_match = re.search(r'I.*P.*O.*(?:Yes|No)', text, re.DOTALL | re.IGNORECASE)
        if not ipo_match:
            return False

        # Check if "Yes" appears before "No" in the match
        ipo_text = ipo_match.group(0)
        yes_pos = ipo_text.find('Yes')
        no_pos = ipo_text.find('No')

        # If Yes appears and comes before No, likely checked
        if yes_pos != -1 and (no_pos == -1 or yes_pos < no_pos):
            # Look for checkbox markers near "Yes"
            if '☒' in ipo_text[:yes_pos+10] or '[X]' in ipo_text[:yes_pos+10]:
                return True

        return False

    def _clean_merged_text(self, text: str) -> str:
        """Clean merged text fields (e.g. missing spaces)."""
        # Insert space between date and date: 202505/01 -> 2025 05/01
        text = re.sub(r'(\d{4})(\d{2}/\d{2})', r'\1 \2', text)
        # Insert space between date and amount: 2025$1,000 -> 2025 $1,000
        text = re.sub(r'(\d{4})(\$)', r'\1 \2', text)
        # Insert space between P/S and date: P05/01 -> P 05/01
        text = re.sub(r'\b([PS])(\d{2}/\d{2})', r'\1 \2', text)
        return text

    def _extract_transactions(self, text: str) -> List[Dict[str, Any]]:
        """Extract transaction records from table."""
        transactions = []

        # Find transaction section (between table header and certification)
        # Handle spaced headers like "I D O w n e r"
        # Handle spaced headers like "I D O w n e r" or "FULL ASSET NAME"
        trans_start_match = re.search(r'(?:ID\s+Owner|I\s*D\s*O\s*w\s*n\s*e\s*r|FULL\s+ASSET\s+NAME)', text, re.IGNORECASE)
        trans_end_match = re.search(r'(?:I\s*CERTIFY|I\s*C\s*E\s*R\s*T\s*I\s*F\s*Y)', text, re.IGNORECASE)
        
        if not trans_start_match:
            logger.warning("Could not find transaction table start")
            return []
            
        trans_start = trans_start_match.end()
        trans_end = trans_end_match.start() if trans_end_match else len(text)

        trans_section = text[trans_start:trans_end]

        # Updated pattern to match actual format:
        # Asset Name (TICKER) [TYPE] TRANS_TYPE DATE DATE AMOUNT
        # Note: Ticker can be at end of asset name line
        # Note: [TYPE] is optional
        # Note: Dates can be smashed together: 01/14/202501/14/2025
        # Note: Amount can span lines
        # Updated pattern to match actual format:
        # Asset Name (TICKER) [TYPE] TRANS_TYPE DATE DATE AMOUNT
        # Note: Ticker can be at end of asset name line
        # Note: [TYPE] is optional
        # Note: Dates can be smashed together: 01/14/202501/14/2025
        # Note: Amount can span lines
        pattern = r'''
            (?:\((?P<ticker>[A-Z]{1,5})\))?            # Ticker in parentheses (optional here, might be in asset name)
            \s*
            (?:\[(?P<type_code>[A-Z]{2,4})\])?         # Asset type code in brackets (optional)
            \s*
            (?P<trans_type>P|S|Purchase|Sale|E)        # Transaction type (E for Exchange)
            \s+
            (?P<trans_date>\d{1,2}/\d{1,2}/\d{4})\s*   # Transaction date (allow no space)
            (?P<notif_date>\d{1,2}/\d{1,2}/\d{4})\s*   # Notification date (allow no space before amount)
            \$?(?P<amount>[\d,]+\s*-\s*\$?[\d,]+|Over\s+\$[\d,]+)  # Amount range
        '''

        # Import reference data
        try:
            from ...reference_data import get_asset_type_description
        except ImportError:
            get_asset_type_description = lambda x: x

        for line in trans_section.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Clean merged text (e.g. 202505/01/2025 or 2025$1,000)
            line = self._clean_merged_text(line)

            match = re.search(pattern, line, re.VERBOSE)
            if match:
                transaction = match.groupdict()
                
                # Post-process fields
                if transaction.get('ticker'):
                    transaction['ticker'] = transaction['ticker'].strip('() ')
                    
                # Clean asset name from previous lines if needed, or if it was captured
                # For now, we assume asset name is in previous lines if not in regex
                # But regex doesn't capture asset name! It captures everything AFTER asset name.
                # We need to get the text BEFORE the match in the line.
                
                # Wait, the regex above matches PART of the line.
                # The asset name is what comes BEFORE the match.
                match_start = match.start()
                asset_name_raw = line[:match_start].strip()
                
                # If asset name is empty, it might be on previous line (handled by loop context?)
                # But here we iterate lines.
                # If asset name is empty, check previous line?
                # For now, just use what we found.
                transaction['asset_name'] = asset_name_raw

                # Enrich with asset type description
                type_code = transaction.get('type_code')
                if type_code:
                    transaction['asset_type'] = get_asset_type_description(type_code)
                    
                # Parse dates
                transaction['transaction_date'] = self.extract_date(transaction.get('trans_date'))
                transaction['notification_date'] = self.extract_date(transaction.get('notif_date'))
                
                # Parse amount
                amount_str = transaction.get('amount', '')
                amount_low, amount_high, amount_range = self.extract_amount_range(amount_str)
                transaction['amount_low'] = amount_low
                transaction['amount_high'] = amount_high
                transaction['amount_range'] = amount_range

                transactions.append(transaction)
                continue



        # Fallback for OCR/Checkbox style forms if no transactions found (or few)
        if len(transactions) == 0:
            logger.info("No standard transactions found, attempting OCR fallback extraction")
            # Pattern: Type Asset ... Date ...
            # Example: Sell Grandeur Peak ... 9/25/25
            fallback_pattern = r'(?P<trans_type>Sell|Buy|Purchase|Sale|Exchange)\s+(?P<asset>.+?)(?P<trans_date>\d{1,2}/\d{1,2}/\d{2,4})'
            
            for line in trans_section.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
            for line in trans_section.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                match = re.search(fallback_pattern, line, re.IGNORECASE)
                if match:
                    trans_type_raw = match.group('trans_type')
                    asset_raw = match.group('asset')
                    trans_date_str = match.group('trans_date')
                    
                    # Clean asset name
                    asset_name = re.sub(r'[|@].*$', '', asset_raw).strip() # Remove garbage like | @ 17.76
                    if len(asset_name) < 3:
                        continue

                    # Determine type
                    if trans_type_raw.lower() in ['p', 'purchase', 'buy']:
                        trans_type = "Purchase"
                    elif trans_type_raw.lower() in ['s', 'sale', 'sell']:
                        trans_type = "Sale"
                    else:
                        trans_type = "Exchange"

                    # Try to find amount (checkbox X)
                    # Very rough heuristic: position of X in the garbage part
                    amount_range = "Unknown"
                    if 'x' in line.lower() or '☒' in line:
                         amount_range = "$1,001 - $15,000" # Default to lowest bucket if X found but position unknown
                         # TODO: Improve column mapping based on X position relative to line length

                    transaction = {
                        "owner_code": "SP",
                        "asset_name": asset_name,
                        "ticker": None,
                        "transaction_type": trans_type,
                        "transaction_date": self.extract_date(trans_date_str),
                        "notification_date": None, # Often missing or same as trans date in fallback
                        "amount_range": amount_range,
                        "amount_low": None,
                        "amount_high": None,
                        "amount_column": None,
                    }
                    transactions.append(transaction)

        logger.info(f"Extracted {len(transactions)} transactions")
        return transactions

    def _map_amount_to_column(self, amount_low: Optional[int], amount_high: Optional[int]) -> Optional[str]:
        """Map amount range to column letter (A-K)."""
        if amount_low is None:
            return None

        # Amount range columns from PTR form
        ranges = [
            (1001, 15000, "A"),
            (15001, 50000, "B"),
            (50001, 100000, "C"),
            (100001, 250000, "D"),
            (250001, 500000, "E"),
            (500001, 1000000, "F"),
            (1000001, 5000000, "G"),
            (5000001, 25000000, "H"),
            (25000001, 50000000, "I"),
            (50000001, None, "J"),  # Over $50M
        ]

        for low, high, column in ranges:
            if amount_low >= low and (high is None or (amount_high and amount_high <= high)):
                return column

        return None

    def _extract_certification(self, text: str) -> Dict[str, Any]:
        """Extract certification information."""
        cert = {
            "filer_certified": False,
            "filer_signature": None,
            "filer_signature_date": None,
            "stock_act_certified": False
        }

        # Look for certification section
        cert_match = re.search(r'(?:I\s*CERTIFY|I\s*C\s*E\s*R\s*T\s*I\s*F\s*Y).*?(?:STOCK\s*Act)', text, re.DOTALL | re.IGNORECASE)
        if cert_match:
            cert["filer_certified"] = True
            cert["stock_act_certified"] = True

        # Extract signature
        sig_match = re.search(r'Digitally Signed:\s*(.+?)\s*,\s*(\d{1,2}/\d{1,2}/\d{4})', text)
        if sig_match:
            cert["filer_signature"] = sig_match.group(1).strip()
            cert["filer_signature_date"] = self.extract_date(sig_match.group(2))

        return cert

    def _calculate_field_confidence(self, filer_info: Dict, transactions: List[Dict],
                                    certification: Dict) -> Dict[str, float]:
        """Calculate per-field confidence scores for audit trail."""
        confidence = {}

        # Filer info confidence
        if filer_info.get("full_name"):
            confidence["filer_info.full_name"] = 0.95 if len(filer_info["full_name"]) > 5 else 0.7
        if filer_info.get("state"):
            confidence["filer_info.state"] = 1.0  # State codes are reliable
        if filer_info.get("district"):
            confidence["filer_info.district"] = 0.98  # District is usually reliable
        if filer_info.get("filer_type"):
            confidence["filer_info.filer_type"] = 0.95

        # Transaction confidence (sample first 3 transactions)
        for i, trans in enumerate(transactions[:3]):
            prefix = f"transactions[{i}]"
            if trans.get("asset_name"):
                confidence[f"{prefix}.asset_name"] = 0.90
            if trans.get("transaction_date"):
                confidence[f"{prefix}.transaction_date"] = 0.95
            if trans.get("amount_range"):
                confidence[f"{prefix}.amount_range"] = 0.88 if "$" in trans["amount_range"] else 0.5

        # Certification confidence
        if certification.get("filer_certified"):
            confidence["certification.filer_certified"] = 1.0
        if certification.get("filer_signature_date"):
            confidence["certification.filer_signature_date"] = 0.95

        return confidence

    def _calculate_data_completeness(self, filer_info: Dict, transactions: List[Dict],
                                     certification: Dict) -> Dict[str, Any]:
        """Calculate data completeness metrics for quality assessment."""
        # Count expected vs extracted fields
        expected_filer_fields = ["full_name", "filer_type", "state", "district"]
        extracted_filer_fields = sum(1 for f in expected_filer_fields if filer_info.get(f))

        expected_cert_fields = ["filer_certified", "filer_signature_date", "stock_act_certified"]
        extracted_cert_fields = sum(1 for f in expected_cert_fields if certification.get(f))

        # Expected transaction fields per transaction
        expected_trans_fields_per = ["asset_name", "transaction_type", "transaction_date",
                                     "notification_date", "amount_range"]
        total_trans_fields_expected = len(transactions) * len(expected_trans_fields_per)
        total_trans_fields_extracted = sum(
            sum(1 for f in expected_trans_fields_per if t.get(f))
            for t in transactions
        )

        # Total fields
        total_expected = len(expected_filer_fields) + len(expected_cert_fields) + total_trans_fields_expected
        total_extracted = extracted_filer_fields + extracted_cert_fields + total_trans_fields_extracted

        # Detect suspicious patterns
        suspicious = []

        # Check for 0 transactions from multi-page PTR
        if len(transactions) == 0:
             suspicious.append(f"0 transactions extracted")

        # Check for all transactions in same amount range
        if len(transactions) > 3:
            amount_ranges = [t.get("amount_range") for t in transactions if t.get("amount_range")]
            if len(set(amount_ranges)) == 1:
                suspicious.append("All transactions in same amount range (suspicious)")

        # Check for missing required fields
        missing = []
        if not filer_info.get("full_name"):
            missing.append("filer_info.full_name")
        if not filer_info.get("filer_type"):
            missing.append("filer_info.filer_type")

        completeness_pct = (total_extracted / total_expected * 100) if total_expected > 0 else 0

        return {
            "total_fields_expected": total_expected,
            "total_fields_extracted": total_extracted,
            "completeness_percentage": round(completeness_pct, 2),
            "missing_required_fields": missing,
            "suspicious_patterns": suspicious
        }
