"""PTR (Periodic Transaction Report) extractor.

Extracts structured data from PTR forms into house_fd_ptr.json schema.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from .base_extractor import BaseExtractor

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
        """Extract filer information from header.

        Args:
            text: Full PDF text

        Returns:
            Filer info dict
        """
        filer_info = {
            "full_name": None,
            "filer_type": None,
            "state": None,
            "district": None
        }

        # Extract name
        name_match = re.search(r'Name:\s*(.+?)(?:\n|Status:)', text, re.IGNORECASE)
        if name_match:
            filer_info["full_name"] = name_match.group(1).strip()

        # Extract status
        status_match = re.search(r'Status:\s*(Member|Officer or Employee)', text, re.IGNORECASE)
        if status_match:
            filer_info["filer_type"] = status_match.group(1).strip()

        # Extract state/district (format: CA11)
        state_dist_match = re.search(r'State/District:\s*([A-Z]{2})(\d{1,2})', text)
        if state_dist_match:
            filer_info["state"] = state_dist_match.group(1)
            filer_info["district"] = state_dist_match.group(2)

        logger.debug(f"Extracted filer info: {filer_info}")
        return filer_info

    def _extract_ipo_question(self, text: str) -> bool:
        """Extract IPO shares allocated question response.

        Args:
            text: Full PDF text

        Returns:
            True if Yes checked, False otherwise
        """
        # Look for IPO section
        ipo_match = re.search(r'I.*P.*O.*(?:Yes|No)', text, re.DOTALL)
        if not ipo_match:
            return False

        # Check if "Yes" appears before "No" in the match
        ipo_text = ipo_match.group(0)
        yes_pos = ipo_text.find('Yes')
        no_pos = ipo_text.find('No')

        # If Yes appears and comes before No, likely checked
        # This is heuristic - better to check for checkbox markers
        if yes_pos != -1 and (no_pos == -1 or yes_pos < no_pos):
            # Look for checkbox markers near "Yes"
            if '☒' in ipo_text[:yes_pos+10] or '[X]' in ipo_text[:yes_pos+10]:
                return True

        return False

    def _extract_transactions(self, text: str) -> List[Dict[str, Any]]:
        """Extract transaction records from table.

        PTR format has transactions split across multiple lines:
        Line 1: Owner + Asset name (first part)
        Line 2: Asset name (continuation) + (TICKER) [TYPE]
        Line 3: TransType Date1 Date2 Amount
        Line N: D: Description

        Args:
            text: Full PDF text

        Returns:
            List of transaction dicts
        """
        transactions = []

        # Find transaction section (between table header and certification)
        trans_start = text.find("ID Owner")
        trans_end = text.find("I CERTIFY")
        if trans_start == -1:
            logger.warning("Could not find transaction table start")
            return []
        if trans_end == -1:
            # Use end of text if certification not found
            trans_end = len(text)

        trans_section = text[trans_start:trans_end]

        # Remove newlines to join multi-line transactions
        # But preserve line breaks at strategic points
        trans_text = trans_section.replace('\n', ' ')

        # Pattern to match complete transaction (now on one line after joining)
        # Format: [Owner] Asset Name (TICKER) [TYPE] TransType Date1 Date2 $Amount
        # Use lookbehind to ensure we start after a space or owner code
        pattern = r'''
            (?:(?<=\s)|(?<=^))                     # Lookbehind for space or start
            (?P<owner>SP|DC|JT)?\s+                # Optional owner code (with space)
            (?P<asset>[\w\s\.\-,]+?)\s+            # Asset name (letters, spaces, dots, hyphens, commas)
            \((?P<ticker>[A-Z]+)\)\s+              # Ticker in parentheses
            \[(?P<type_code>[A-Z]{2})\]\s+         # Asset type code in brackets
            (?P<trans_type>[PS])\s+                # Transaction type
            (?:\(partial\))?\s*                    # Optional "(partial)"
            (?P<trans_date>\d{2}/\d{2}/\d{4})      # Transaction date
            (?P<notif_date>\d{2}/\d{2}/\d{4})      # Notification date (may be joined)
            \s*\$?(?P<amount>[\d,]+\s*-\s*\$?[\d,]+|Over\s+\$?[\d,]+) # Amount
        '''

        for match in re.finditer(pattern, trans_text, re.VERBOSE | re.IGNORECASE):
            owner_code = match.group('owner')
            asset_name = match.group('asset').strip()
            ticker = match.group('ticker')
            asset_type_code = match.group('type_code')
            trans_type_code = match.group('trans_type')
            trans_date_str = match.group('trans_date')
            notif_date_str = match.group('notif_date')
            amount_str = match.group('amount')

            # Clean up asset name (remove extra spaces, owner code if present)
            if owner_code:
                asset_name = asset_name.replace(owner_code, '').strip()

            # Determine transaction type
            trans_type = "Purchase" if trans_type_code == "P" else "Sale"
            if "(partial)" in match.group(0):
                trans_type = "Partial Sale"

            # Parse dates
            trans_date = self.extract_date(trans_date_str)
            notif_date = self.extract_date(notif_date_str)

            # Parse amount
            amount_low, amount_high, amount_range = self.extract_amount_range(amount_str)

            # Extract description (look for "D:" after this transaction)
            desc_pattern = rf'{re.escape(match.group(0))}.*?D\s*:\s*(.+?)(?=(?:SP|DC|JT)?\s+\w+.*?\([A-Z]+\)\s+\[[A-Z]{{2}}\]|F\s+S\s+:|$)'
            desc_match = re.search(desc_pattern, trans_text, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else None

            transaction = {
                "owner_code": owner_code,
                "asset_name": f"{asset_name} - ({ticker})",
                "transaction_type": trans_type,
                "transaction_date": trans_date,
                "notification_date": notif_date,
                "amount_range": amount_range,
                "amount_low": amount_low,
                "amount_high": amount_high,
                "amount_column": self._map_amount_to_column(amount_low, amount_high),
            }

            transactions.append(transaction)

        logger.info(f"Extracted {len(transactions)} transactions")
        return transactions

    def _map_amount_to_column(self, amount_low: Optional[int], amount_high: Optional[int]) -> Optional[str]:
        """Map amount range to column letter (A-K).

        Args:
            amount_low: Lower bound of range
            amount_high: Upper bound of range

        Returns:
            Column letter (A-K) or None
        """
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
        """Extract certification information.

        Args:
            text: Full PDF text

        Returns:
            Certification dict
        """
        cert = {
            "filer_certified": False,
            "filer_signature": None,
            "filer_signature_date": None,
            "stock_act_certified": False
        }

        # Look for certification section
        cert_match = re.search(r'I CERTIFY that the statements.*?STOCK Act', text, re.DOTALL | re.IGNORECASE)
        if cert_match:
            cert["filer_certified"] = True
            cert["stock_act_certified"] = True

        # Extract signature
        sig_match = re.search(r'Digitally Signed:\s*(.+?)\s*,\s*(\d{2}/\d{2}/\d{4})', text)
        if sig_match:
            cert["filer_signature"] = sig_match.group(1).strip()
            cert["filer_signature_date"] = self.extract_date(sig_match.group(2))

        return cert

    def _calculate_field_confidence(self, filer_info: Dict, transactions: List[Dict],
                                    certification: Dict) -> Dict[str, float]:
        """Calculate per-field confidence scores for audit trail.

        Args:
            filer_info: Extracted filer information
            transactions: List of extracted transactions
            certification: Extracted certification info

        Returns:
            Dict mapping field paths to confidence scores (0-1)
        """
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
        """Calculate data completeness metrics for quality assessment.

        Args:
            filer_info: Extracted filer information
            transactions: List of extracted transactions
            certification: Extracted certification info

        Returns:
            Completeness metrics dict
        """
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
        if len(transactions) == 0 and hasattr(self.analyzer, 'reader'):
            page_count = len(self.analyzer.reader.pages)
            if page_count >= 2:
                suspicious.append(f"0 transactions extracted from {page_count}-page PTR")

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
