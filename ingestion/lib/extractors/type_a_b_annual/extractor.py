"""Type A/B (Annual/New Filer) extractor.

Extracts structured data from Form A (Annual) and Form B (New Filer) reports.
"""

import logging
import re
from typing import Dict, List, Any, Optional
from ..base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class TypeABAnnualExtractor(BaseExtractor):
    """Extract structured data from Annual and New Filer reports."""

    def extract_from_text(self, text: str, pdf_properties: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract Form A/B data from text.

        Args:
            text: Extracted text from PDF
            pdf_properties: Optional PDF metadata

        Returns:
            Structured data matching house_fd_annual.json schema
        """
        pdf_properties = pdf_properties or {}
        logger.info("Extracting Annual/New Filer data from text")

        # Clean text of null bytes and excessive whitespace
        text = text.replace('\x00', '')

        # Extract sections
        filer_info = self._extract_filer_info(text)
        
        # Extract main schedules
        assets = self._extract_assets_and_income(text)
        earned_income = self._extract_earned_income(text)
        liabilities = self._extract_liabilities(text)
        positions = self._extract_positions(text)
        agreements = self._extract_agreements(text)
        gifts = self._extract_gifts(text)
        travel = self._extract_travel(text)
        charity = self._extract_charity(text)
        
        # Extract certification
        certification = self._extract_certification(text)

        # Calculate confidence and completeness
        field_confidence = self._calculate_field_confidence(filer_info, assets, certification)
        completeness_metrics = self._calculate_data_completeness(
            filer_info, assets, liabilities, positions, agreements, certification
        )
        
        overall_confidence = sum(field_confidence.values()) / len(field_confidence) if field_confidence else 0.5
        
        # Recommend Textract if confidence is low or critical data is missing
        textract_recommended = (
            overall_confidence < 0.70 or
            completeness_metrics["overall_completeness"] < 0.60 or
            len(completeness_metrics["missing_critical_fields"]) > 0
        )

        result = {
            "filer_info": filer_info,
            "report_type": {
                "is_amendment": False,  # TODO: detect
                "filing_type": filer_info.get("filing_type", "A") 
            },
            "schedule_a": assets,
            "schedule_c": earned_income,
            "schedule_d": liabilities,
            "schedule_e": positions,
            "schedule_f": agreements,
            "schedule_g": gifts,
            "schedule_h": travel,
            "schedule_i": charity,
            "certification": certification,
            "filing_metadata": {
                "asset_count": len(assets),
                "liability_count": len(liabilities),
                "position_count": len(positions),
                "agreement_count": len(agreements),
                "gift_count": len(gifts),
                "travel_count": len(travel)
            },
            "data_quality": {
                "completeness_metrics": completeness_metrics,
                "confidence_score": overall_confidence,
                "textract_recommended": textract_recommended,
                "extraction_issues": completeness_metrics["missing_critical_fields"]
            },
            "extraction_metadata": self.create_extraction_metadata(
                confidence=overall_confidence,
                method="regex",
                field_confidence=field_confidence
            )
        }
        
        # Add textract recommendation to metadata
        result["extraction_metadata"]["textract_recommended"] = textract_recommended
        result["extraction_metadata"]["missing_fields"] = completeness_metrics["missing_critical_fields"]

        return result

    def _extract_filer_info(self, text: str) -> Dict[str, Any]:
        """Extract filer information from header."""
        from .field_extractors import normalize_date_format
        
        filer_info = {
            "full_name": None,
            "filer_type": None,
            "position": None,
            "state": None,
            "district": None,
            "state_district": None,
            "year": None,
            "filing_period_start": None,
            "filing_period_end": None,
            "filing_type": "A"  # Default to Annual
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
        # Added "Candidate" and "Former Member" to regex
        status_match = re.search(r'Status:\s*(Member|Officer\s+or\s+Employee|Employee|Congressional\s+Candidate|Candidate|Former\s+Member)', text, re.IGNORECASE)
        if status_match:
            filer_info["filer_type"] = status_match.group(1).strip()

        # Extract position/office
        position_patterns = [
            r'Office:\s*(.+?)(?:\n|State:)',
            r'Position:\s*(.+?)(?:\n|State:)',
            r'(?:Representative|Senator)\s+for\s+(.+?)(?:\n|,)',
        ]
        
        for pattern in position_patterns:
            pos_match = re.search(pattern, text, re.IGNORECASE)
            if pos_match:
                filer_info["position"] = pos_match.group(1).strip()
                break
        
        # If we found "Member" as type and no position, try to infer
        if filer_info["filer_type"] == "Member" and not filer_info["position"]:
            if re.search(r'House of Representatives', text, re.IGNORECASE):
                filer_info["position"] = "U.S. Representative"
            elif re.search(r'Senate|Senator', text, re.IGNORECASE):
                filer_info["position"] = "U.S. Senator"

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
                filer_info["state_district"] = f"{state}{district.zfill(2)}"
                break
        
        # If no district found, might be Senate (statewide)
        if not filer_info["state"] and not filer_info["district"]:
            state_only_match = re.search(r'State:\s*([A-Z]{2})\b', text)
            if state_only_match:
                filer_info["state"] = state_only_match.group(1)
                filer_info["state_district"] = filer_info["state"]
            
        # Detect filing type (Annual vs New Filer vs Candidate)
        if any(x in text for x in ["New Filer", "Form B", "Candidate", "Initial Report"]):
            filer_info["filing_type"] = "N" if "New Filer" in text else "B"
        elif "Termination" in text:
            filer_info["filing_type"] = "T"
        else:
            filer_info["filing_type"] = "A"  # Annual is default
            
        # Extract calendar year
        year_patterns = [
            r'Calendar Year:\s*(\d{4})',
            r'Reporting Year:\s*(\d{4})',
            r'Year:\s*(\d{4})',
            r'Filing Year:\s*(\d{4})',
            r'\b(20\d{2})\b',  # Generic 4-digit year
        ]
        
        for pattern in year_patterns:
            year_match = re.search(pattern, text)
            if year_match:
                year = int(year_match.group(1))
                if 2012 <= year <= 2030:
                    filer_info["year"] = year
                    break
                    
        # Extract filing period dates
        period_match = re.search(
            r'Filing Period:\s*(\d{1,2}/\d{1,2}/\d{4})\s*(?:to|through|[-–])\s*(\d{1,2}/\d{1,2}/\d{4})',
            text,
            re.IGNORECASE
        )
        if period_match:
            filer_info["filing_period_start"] = normalize_date_format(period_match.group(1))
            filer_info["filing_period_end"] = normalize_date_format(period_match.group(2))

        return filer_info

    def _extract_assets_and_income(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule A: Assets and "Unearned" Income."""
        from .field_extractors import (
            extract_asset_value_range,
            extract_income_type,
            parse_owner_code,
            extract_asset_type,
            extract_ticker_symbol,
            clean_asset_name,
            map_value_to_disclosure_category
        )
        
        assets = []
        
        # Find Schedule A section - handle "S A: A 'U' I" and other variations
        section_match = re.search(
            r'(?:Schedule\s+A|S\s*A).*?(?:Assets|A\s*"U"\s*I).*?\n(.*?)(?=\n\s*(?:Schedule|S)\s+[BCDEFGHI]|\n\s*Part\s+[IVX]{1,4}|\Z)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        
        if not section_match:
            return []
            
        section_text = section_match.group(1)
        lines = section_text.split('\n')
        asset_buffer = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped or len(line_stripped) < 3:
                continue
            # Skip headers and footers
            if re.search(r'Owner|Asset|Income|Description|Value|Type|Investment|Vehicle|abbreviations|house\.gov|Current Year|Preceding Year|Filing Year', line_stripped, re.IGNORECASE):
                continue
            if "None disclosed" in line_stripped:
                continue
            if "I CERTIFY" in line_stripped or "Digitally Signed" in line_stripped:
                break
                
            # Check if line contains a value range
            has_value_range = re.search(r'(\$[\d,]+\s*[-–]\s*\$[\d,]+|Over\s+\$[\d,]+)', line_stripped)
            
            asset_buffer.append(line_stripped)
            
            # Safety valve for buffer size
            if len(asset_buffer) > 10:
                asset_buffer = []
                continue
            
            if has_value_range:
                # End of entry, parse buffer
                full_entry = ' '.join(asset_buffer)
                asset_data = self._parse_asset_entry(full_entry)
                if asset_data:
                    assets.append(asset_data)
                asset_buffer = []
        
        return assets
    
    def _parse_asset_entry(self, entry_text: str) -> Optional[Dict[str, Any]]:
        """Parse a single asset entry."""
        from .field_extractors import (
            extract_asset_value_range,
            extract_income_type,
            parse_owner_code,
            extract_asset_type,
            extract_ticker_symbol,
            clean_asset_name,
            map_value_to_disclosure_category
        )
        
        if not entry_text or len(entry_text) < 5:
            return None
        
        asset = {
            "asset_name": None,
            "owner_code": parse_owner_code(entry_text),
            "description": entry_text,
            "asset_type": None,
            "ticker_symbol": None,
            "value_low": None,
            "value_high": None,
            "value_category": None,
            "income_type": None,
            "income_amount_low": None,
            "income_amount_high": None,
            "income_category": None
        }
        
        # Handle smashed text: "$15,001 - $50,000Dividends"
        entry_text = re.sub(r'(\$[\d,]+)(Dividends|Interest|Rent|Capital|None)', r'\1 \2', entry_text)
        
        value_range_match = re.search(r'(\$[\d,]+\s*[-–]\s*\$[\d,]+|Over\s+\$[\d,]+|None(?:\s+\(or\s+less\s+than\s+\$[\d,]+\))?)', entry_text, re.IGNORECASE)
        if not value_range_match:
            # Require a value range for a valid asset
            return None
            
        value_text = value_range_match.group(1)
        asset["value_low"], asset["value_high"] = extract_asset_value_range(value_text)
        if asset["value_low"] is not None:
            asset["value_category"] = map_value_to_disclosure_category(asset["value_low"], asset["value_high"])
        
        income_match = re.search(r'(Dividend|Interest|Rent|Capital Gain|None|Royalt|Earned)', entry_text, re.IGNORECASE)
        if income_match:
            asset["income_type"] = extract_income_type(income_match.group(1))
            all_ranges = re.findall(r'\$[\d,]+\s*[-–]\s*\$[\d,]+', entry_text)
            if len(all_ranges) >= 2:
                income_range_text = all_ranges[-1]
                asset["income_amount_low"], asset["income_amount_high"] = extract_asset_value_range(income_range_text)
                if asset["income_amount_low"] is not None:
                    asset["income_category"] = map_value_to_disclosure_category(asset["income_amount_low"], asset["income_amount_high"])
            elif income_match.group(1).lower() == 'none':
                asset["income_amount_low"] = 0
                asset["income_amount_high"] = 0
                asset["income_category"] = "None"
        
        name_text = entry_text
        owner_prefix_match = re.match(r'^(?:SP|DC|JT|Self|Joint|Spouse|Child)\s+', name_text, re.IGNORECASE)
        if owner_prefix_match:
            name_text = name_text[owner_prefix_match.end():]
        name_text = re.sub(r'^\d{1,3}[\.\)]\s+', '', name_text)
        
        if value_range_match:
            name_text = name_text[:value_range_match.start()]
        
        asset["asset_name"] = clean_asset_name(name_text)
        asset["asset_type"] = extract_asset_type(asset["asset_name"])
        
        if asset["asset_type"] in ["Stock", "ETF", "Stock Option"]:
            asset["ticker_symbol"] = extract_ticker_symbol(asset["asset_name"])
        
        if not asset["asset_name"] or len(asset["asset_name"]) < 3:
            return None
        
        return asset

    def _extract_earned_income(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule C: Earned Income."""
        income = []
        section_match = re.search(r'(?:Schedule\s+C|S\s*C).*?\n(.*?)(?=\n\s*(?:Schedule|S)\s+[DEFGHI]|\n\s*Part|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or "None disclosed" in line: continue
                if re.search(r'Source|Type|Amount|Current Year|Preceding Year', line, re.IGNORECASE): continue
                
                structured_match = re.search(r'Source:\s*(.*?)(?:\s+Type:|\s+Amount:|$)', line, re.IGNORECASE)
                if structured_match:
                    income.append({
                        "source": structured_match.group(1).strip(),
                        "type": "Earned Income",
                        "amount": None
                    })
                    continue

                if len(line.split()) >= 2 and len(line) < 200 and re.match(r'^[A-Z]', line):
                    income.append({
                        "source": line,
                        "type": "Earned Income",
                        "amount": None 
                    })
        return income

    def _extract_liabilities(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule D: Liabilities."""
        liabilities = []
        section_match = re.search(r'(?:Schedule\s+D|S\s*D).*?\n(.*?)(?=\n\s*(?:Schedule|S)\s+[EFGHI]|\n\s*Part|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or "None disclosed" in line: continue
                if re.search(r'Creditor|Date|Incurred|Amount', line, re.IGNORECASE): continue
                
                has_value_range = re.search(r'(\$[\d,]+\s*[-–]\s*\$[\d,]+|Over\s+\$[\d,]+)', line)
                if has_value_range:
                    liabilities.append({
                        "creditor_name": line[:has_value_range.start()].strip(),
                        "owner_code": self.extract_owner_code(line)
                    })
        return liabilities

    def _extract_positions(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule E: Positions."""
        positions = []
        section_match = re.search(r'(?:Schedule\s+E|S\s*E).*?\n(.*?)(?=\n\s*(?:Schedule|S)\s+[FGHI]|\n\s*Part|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or "None disclosed" in line: continue
                if re.search(r'Position|Name|Organization', line, re.IGNORECASE): continue
                
                if len(line) > 5 and len(line) < 200 and re.match(r'^[A-Z]', line):
                    positions.append({
                        "position_title": line
                    })
        return positions

    def _extract_agreements(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule F: Agreements."""
        agreements = []
        section_match = re.search(r'(?:Schedule\s+F|S\s*F).*?\n(.*?)(?=\n\s*(?:Schedule|S)\s+[GHI]|\n\s*Part|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or "None disclosed" in line: continue
                if re.search(r'Date|Parties|Terms', line, re.IGNORECASE): continue
                
                if len(line) > 10 and re.match(r'^[A-Z]', line):
                    agreements.append({
                        "agreement_description": line
                    })
        return agreements

    def _extract_gifts(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule G: Gifts."""
        gifts = []
        section_match = re.search(r'(?:Schedule\s+G|S\s*G).*?\n(.*?)(?=\n\s*(?:Schedule|S)\s+[HI]|\n\s*Part|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or "None disclosed" in line: continue
                if re.search(r'Source|Description|Value', line, re.IGNORECASE): continue
                
                if len(line) > 5 and re.match(r'^[A-Z]', line):
                    gifts.append({
                        "source": line
                    })
        return gifts

    def _extract_travel(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule H: Travel."""
        travel = []
        section_match = re.search(r'(?:Schedule\s+H|S\s*H).*?\n(.*?)(?=\n\s*(?:Schedule|S)\s+[I]|\n\s*Part|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or "None disclosed" in line: continue
                if re.search(r'Source|Date|City|State', line, re.IGNORECASE): continue
                
                if len(line) > 5 and re.match(r'^[A-Z]', line):
                    travel.append({
                        "source": line
                    })
        return travel

    def _extract_charity(self, text: str) -> List[Dict[str, Any]]:
        """Extract Schedule I: Charity."""
        charity = []
        section_match = re.search(r'(?:Schedule\s+I|S\s*I).*?\n(.*?)(?=\n\s*(?:Schedule|S)|\Z)', 
                                 text, re.DOTALL | re.IGNORECASE)
        if section_match:
            section_text = section_match.group(1)
            lines = section_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or "None disclosed" in line: continue
                if re.search(r'Source|Date|Amount', line, re.IGNORECASE): continue
                
                if len(line) > 5 and re.match(r'^[A-Z]', line):
                    charity.append({
                        "source": line
                    })
        return charity

    def _extract_certification(self, text: str) -> Dict[str, Any]:
        """Extract certification information."""
        cert = {
            "filer_certified": False,
            "filer_signature": None,
            "filer_signature_date": None
        }

        if "I CERTIFY" in text:
            cert["filer_certified"] = True

        sig_match = re.search(r'Digitally Signed:\s*(.+?)\s*,\s*(\d{1,2}/\d{1,2}/\d{4})', text)
        if sig_match:
            cert["filer_signature"] = sig_match.group(1).strip()
            cert["filer_signature_date"] = self.extract_date(sig_match.group(2))

        return cert

    def _calculate_field_confidence(self, filer_info: Dict, assets: List[Dict], cert: Dict) -> Dict[str, float]:
        """Calculate per-field confidence scores."""
        confidence = {}
        
        # Filer info confidence
        if filer_info.get("full_name"):
            name = filer_info["full_name"]
            if len(name.split()) >= 2:
                confidence["filer_info.full_name"] = 0.95
            else:
                confidence["filer_info.full_name"] = 0.60
        else:
            confidence["filer_info.full_name"] = 0.0
            
        if filer_info.get("filer_type"):
            confidence["filer_info.filer_type"] = 0.90
        else:
            confidence["filer_info.filer_type"] = 0.0
            
        if filer_info.get("state"):
            confidence["filer_info.state"] = 0.95
        else:
            confidence["filer_info.state"] = 0.0
            
        if filer_info.get("year"):
            confidence["filer_info.year"] = 1.0
        else:
            confidence["filer_info.year"] = 0.0
            
        # Assets confidence
        if assets:
            asset_confidences = []
            for asset in assets:
                asset_conf = 0.0
                fields_checked = 0
                if asset.get("asset_name") and len(asset["asset_name"]) > 3:
                    asset_conf += 1.0
                fields_checked += 1
                if asset.get("owner_code"):
                    asset_conf += 1.0
                fields_checked += 1
                if asset.get("value_low") is not None:
                    asset_conf += 1.0
                fields_checked += 1
                if asset.get("asset_type") and asset["asset_type"] != "Unknown":
                    asset_conf += 0.5
                fields_checked += 1
                if fields_checked > 0:
                    asset_confidences.append(asset_conf / fields_checked)
            
            if asset_confidences:
                avg_confidence = sum(asset_confidences) / len(asset_confidences)
                confidence["assets.overall"] = avg_confidence
                confidence["assets.count"] = len(assets) / max(len(assets) + 10, 50)
            else:
                confidence["assets.overall"] = 0.0
        else:
            confidence["assets.overall"] = 0.0
            
        # Certification confidence
        if cert.get("filer_certified"):
            confidence["certification.certified"] = 1.0
        else:
            confidence["certification.certified"] = 0.3
            
        if cert.get("filer_signature"):
            confidence["certification.signature"] = 0.95
        else:
            confidence["certification.signature"] = 0.0
        
        return confidence
    
    def _calculate_data_completeness(self, filer_info: Dict, assets: List[Dict], 
                                    liabilities: List[Dict], positions: List[Dict],
                                    agreements: List[Dict], certification: Dict) -> Dict[str, Any]:
        """Calculate data completeness metrics."""
        metrics = {
            "filer_info_completeness": 0.0,
            "schedule_a_completeness": 0.0,
            "schedule_d_completeness": 0.0,
            "overall_completeness": 0.0,
            "missing_critical_fields": [],
            "populated_schedules": []
        }
        
        filer_fields = ["full_name", "filer_type", "state", "year", "filing_type"]
        filer_populated = sum(1 for f in filer_fields if filer_info.get(f))
        metrics["filer_info_completeness"] = filer_populated / len(filer_fields)
        
        if not filer_info.get("full_name"):
            metrics["missing_critical_fields"].append("filer_info.full_name")
        if not filer_info.get("year"):
            metrics["missing_critical_fields"].append("filer_info.year")
        
        if assets:
            complete_assets = 0
            for asset in assets:
                required_fields = ["asset_name", "owner_code", "value_low"]
                if all(asset.get(f) for f in required_fields):
                    complete_assets += 1
            
            metrics["schedule_a_completeness"] = complete_assets / len(assets) if assets else 0.0
            metrics["populated_schedules"].append("Schedule A (Assets)")
            metrics["schedule_a_asset_count"] = len(assets)
            metrics["schedule_a_complete_count"] = complete_assets
        else:
            metrics["schedule_a_completeness"] = 0.0
            
        if liabilities:
            metrics["schedule_d_completeness"] = 1.0
            metrics["populated_schedules"].append("Schedule D (Liabilities)")
            metrics["schedule_d_count"] = len(liabilities)
        else:
            metrics["schedule_d_completeness"] = 0.0
            
        if positions:
            metrics["populated_schedules"].append("Schedule E (Positions)")
            metrics["schedule_e_count"] = len(positions)
            
        if agreements:
            metrics["populated_schedules"].append("Schedule F (Agreements)")
            metrics["schedule_f_count"] = len(agreements)
        
        cert_fields = ["filer_certified", "filer_signature"]
        cert_populated = sum(1 for f in cert_fields if certification.get(f))
        metrics["certification_completeness"] = cert_populated / len(cert_fields)
        
        metrics["overall_completeness"] = (
            metrics["filer_info_completeness"] * 0.3 +
            metrics["schedule_a_completeness"] * 0.5 +
            metrics["certification_completeness"] * 0.2
        )
        
        return metrics
