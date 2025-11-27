"""Form A/B (Annual & Candidate Financial Disclosure) extractor.

Extracts structured data from Form A (Annual/Termination) and Form B (Candidate/New Filer)
reports into house_fd_form_ab.json schema.

Form A/B includes 9 schedules:
- Schedule A: Assets and Unearned Income
- Schedule B: Transactions (same as PTR)
- Schedule C: Earned Income
- Schedule D: Liabilities
- Schedule E: Outside Positions
- Schedule F: Agreements and Arrangements
- Schedule G: Gifts
- Schedule H: Travel Reimbursements
- Schedule I: Charity Contributions (not always present)
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FormABExtractor:
    """Extract structured data from Form A/B financial disclosures."""

    def __init__(self):
        """Initialize the extractor."""
        self.extraction_version = "1.0.0"

    def extract_from_textract(
        self,
        doc_id: str,
        year: int,
        textract_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract Form A/B data from Textract blocks.

        Args:
            doc_id: Document ID
            year: Filing year
            textract_blocks: List of Textract block dictionaries

        Returns:
            Structured data matching house_fd_form_ab.json schema
        """
        logger.info(f"Extracting Form A/B data for doc_id={doc_id}, year={year}")

        # Build block map for efficient lookups
        block_map = {block["Id"]: block for block in textract_blocks}

        # Extract header information
        header = self._extract_header(textract_blocks, block_map)

        # Extract Part I checkboxes (yes/no questions)
        part_i = self._extract_part_i(textract_blocks, block_map)

        # Extract tables and route to appropriate schedules
        tables = self._extract_tables(textract_blocks, block_map)
        schedules = self._route_to_schedules(tables, textract_blocks)

        # Extract Exclusions section (2 Yes/No questions)
        exclusions = self._extract_exclusions(textract_blocks, block_map)

        # Extract Certification section (checkbox + signature)
        certification = self._extract_certification(textract_blocks, block_map)

        # Calculate overall confidence
        confidence = self._calculate_confidence(header, part_i, schedules)

        # Build structured output
        result = {
            "doc_id": doc_id,
            "year": year,
            "filing_type": header.get("filing_type", "Annual Report"),
            "header": header,
            "part_i_questions": part_i,
            "schedule_a_assets": schedules.get("schedule_a", []),
            "schedule_c_earned_income": schedules.get("schedule_c", []),
            "schedule_d_liabilities": schedules.get("schedule_d", []),
            "schedule_e_positions": schedules.get("schedule_e", []),
            "schedule_f_agreements": schedules.get("schedule_f", []),
            "schedule_g_gifts": schedules.get("schedule_g", []),
            "schedule_h_travel": schedules.get("schedule_h", []),
            "schedule_i_charity": schedules.get("schedule_i", []),
            "schedule_j_compensation": schedules.get("schedule_j", []),
            "exclusions": exclusions,  # NEW
            "certification": certification,  # NEW
            "extraction_metadata": {
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "extraction_method": "textract_forms_tables",
                "extraction_version": self.extraction_version,
                "overall_confidence": confidence,
                "total_pages": self._get_page_count(textract_blocks)
            }
        }

        return result

    def _extract_header(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract document header fields.

        Args:
            blocks: Textract blocks
            block_map: Block ID to block mapping

        Returns:
            Header information dictionary
        """
        header = {
            "filer_name": None,
            "title_status": None,
            "state_district": None,
            "reporting_period_from": None,
            "reporting_period_to": None,
            "filing_date": None,
            "filing_type": None,
            "is_amendment": False
        }

        # Extract key-value pairs from FORMS blocks
        kv_pairs = self._extract_key_value_pairs(blocks, block_map)

        # Map known fields
        field_mappings = {
            "Name": "filer_name",
            "Filer Name": "filer_name",
            "Title": "title_status",
            "Status": "title_status",
            "State/District": "state_district",
            "Reporting Period": "reporting_period",
            "Filing Date": "filing_date",
            "Filing Type": "filing_type"
        }

        for textract_key, header_key in field_mappings.items():
            if textract_key in kv_pairs and kv_pairs[textract_key]:
                header[header_key] = kv_pairs[textract_key].strip()

        # Parse reporting period if in "MM/DD/YYYY - MM/DD/YYYY" format
        if "reporting_period" in header and header["reporting_period"]:
            period_match = re.search(
                r'(\d{1,2}/\d{1,2}/\d{4})\s*-\s*(\d{1,2}/\d{1,2}/\d{4})',
                header["reporting_period"]
            )
            if period_match:
                header["reporting_period_from"] = period_match.group(1)
                header["reporting_period_to"] = period_match.group(2)
            del header["reporting_period"]  # Remove raw field

        # Check for amendment
        header["is_amendment"] = any(
            "amendment" in str(v).lower()
            for v in header.values()
            if v
        )

        logger.debug(f"Extracted header: {header}")
        return header

    def _extract_part_i(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Optional[bool]]:
        """Extract Part I checkbox questions.

        Part I typically includes yes/no questions about:
        - Qualified Blind Trust
        - Qualified Diversified Trust
        - Excepted Investment Fund
        - Exemption from reporting asset values

        Args:
            blocks: Textract blocks
            block_map: Block ID to block mapping

        Returns:
            Dictionary of question key to boolean (True=Yes, False=No, None=Not found)
        """
        part_i = {
            "qualified_blind_trust": None,
            "qualified_diversified_trust": None,
            "excepted_investment_fund": None,
            "exemption_granted": None
        }

        # Find SELECTION_ELEMENT blocks (checkboxes)
        for block in blocks:
            if block.get("BlockType") != "SELECTION_ELEMENT":
                continue

            is_selected = block.get("SelectionStatus") == "SELECTED"

            # Find nearby text to identify which question this checkbox relates to
            nearby_text = self._get_nearby_text(block, blocks)
            nearby_lower = nearby_text.lower()

            # Match to questions based on nearby text
            if "blind trust" in nearby_lower and "qualified" in nearby_lower:
                if "yes" in nearby_lower:
                    part_i["qualified_blind_trust"] = is_selected
                elif "no" in nearby_lower:
                    part_i["qualified_blind_trust"] = not is_selected

            if "diversified trust" in nearby_lower and "qualified" in nearby_lower:
                if "yes" in nearby_lower:
                    part_i["qualified_diversified_trust"] = is_selected
                elif "no" in nearby_lower:
                    part_i["qualified_diversified_trust"] = not is_selected

            if "excepted investment fund" in nearby_lower:
                if "yes" in nearby_lower:
                    part_i["excepted_investment_fund"] = is_selected
                elif "no" in nearby_lower:
                    part_i["excepted_investment_fund"] = not is_selected

            if "exemption" in nearby_lower and "granted" in nearby_lower:
                if "yes" in nearby_lower:
                    part_i["exemption_granted"] = is_selected
                elif "no" in nearby_lower:
                    part_i["exemption_granted"] = not is_selected

        logger.debug(f"Extracted Part I questions: {part_i}")
        return part_i

    def _extract_tables(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Extract all TABLE blocks from Textract response.

        Args:
            blocks: Textract blocks
            block_map: Block ID to block mapping

        Returns:
            List of parsed tables, each containing header and rows
        """
        tables = []

        for block in blocks:
            if block.get("BlockType") != "TABLE":
                continue

            # Parse table into rows and columns
            table_data = self._parse_table_block(block, block_map)
            if table_data:
                tables.append(table_data)

        logger.debug(f"Extracted {len(tables)} tables")
        return tables

    def _parse_table_block(
        self,
        table_block: Dict[str, Any],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Parse a single TABLE block into structured data.

        Args:
            table_block: TABLE block from Textract
            block_map: Block ID to block mapping

        Returns:
            Dictionary with 'headers' and 'rows' keys, or None if parsing fails
        """
        relationships = table_block.get("Relationships", [])
        cells = []

        # Get all CELL blocks in this table
        for relationship in relationships:
            if relationship.get("Type") == "CHILD":
                for cell_id in relationship.get("Ids", []):
                    if cell_id in block_map:
                        cell_block = block_map[cell_id]
                        if cell_block.get("BlockType") == "CELL":
                            cells.append(cell_block)

        if not cells:
            return None

        # Organize cells into rows and columns
        rows_dict = {}
        for cell in cells:
            row_index = cell.get("RowIndex", 1)
            col_index = cell.get("ColumnIndex", 1)

            # Get cell text
            cell_text = self._get_cell_text(cell, block_map)

            if row_index not in rows_dict:
                rows_dict[row_index] = {}
            rows_dict[row_index][col_index] = cell_text

        # Convert to list of lists
        max_row = max(rows_dict.keys()) if rows_dict else 0
        max_col = max(
            max(row.keys()) for row in rows_dict.values()
        ) if rows_dict else 0

        table_matrix = []
        for row_idx in range(1, max_row + 1):
            row = []
            for col_idx in range(1, max_col + 1):
                row.append(rows_dict.get(row_idx, {}).get(col_idx, ""))
            table_matrix.append(row)

        if not table_matrix:
            return None

        # First row is typically the header
        return {
            "headers": table_matrix[0] if table_matrix else [],
            "rows": table_matrix[1:] if len(table_matrix) > 1 else [],
            "row_count": len(table_matrix) - 1,
            "column_count": max_col
        }

    def _route_to_schedules(
        self,
        tables: List[Dict[str, Any]],
        blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Route extracted tables to appropriate schedules based on headers.

        Args:
            tables: List of parsed tables
            blocks: All Textract blocks (for context)

        Returns:
            Dictionary of schedule name to schedule data
        """
        from .schedules.schedule_a_extractor import ScheduleAExtractor
        from .schedules.schedule_c_extractor import ScheduleCExtractor
        from .schedules.schedule_d_extractor import ScheduleDExtractor
        from .schedules.schedule_e_extractor import ScheduleEExtractor
        from .schedules.schedule_f_extractor import ScheduleFExtractor
        from .schedules.schedule_g_extractor import ScheduleGExtractor
        from .schedules.schedule_h_extractor import ScheduleHExtractor
        from .schedules.schedule_i_extractor import ScheduleIExtractor

        schedules = {}

        # Initialize schedule extractors
        schedule_a_extractor = ScheduleAExtractor()
        schedule_c_extractor = ScheduleCExtractor()
        schedule_d_extractor = ScheduleDExtractor()
        schedule_e_extractor = ScheduleEExtractor()
        schedule_f_extractor = ScheduleFExtractor()
        schedule_g_extractor = ScheduleGExtractor()
        schedule_h_extractor = ScheduleHExtractor()
        schedule_i_extractor = ScheduleIExtractor()

        for table in tables:
            # Classify table based on headers
            schedule_type = self._classify_table(table)

            if schedule_type == "schedule_a":
                assets = schedule_a_extractor.parse_table(table)
                schedules.setdefault("schedule_a", []).extend(assets)

            elif schedule_type == "schedule_c":
                income = schedule_c_extractor.parse_table(table)
                schedules.setdefault("schedule_c", []).extend(income)

            elif schedule_type == "schedule_d":
                liabilities = schedule_d_extractor.parse_table(table)
                schedules.setdefault("schedule_d", []).extend(liabilities)

            elif schedule_type == "schedule_e":
                positions = schedule_e_extractor.parse_table(table)
                schedules.setdefault("schedule_e", []).extend(positions)
            
            elif schedule_type == "schedule_f":
                agreements = schedule_f_extractor.parse_table(table)
                schedules.setdefault("schedule_f", []).extend(agreements)

            elif schedule_type == "schedule_g":
                gifts = schedule_g_extractor.parse_table(table)
                schedules.setdefault("schedule_g", []).extend(gifts)

            elif schedule_type == "schedule_h":
                travel = schedule_h_extractor.parse_table(table)
                schedules.setdefault("schedule_h", []).extend(travel)

            elif schedule_type == "schedule_i":
                contributions = schedule_i_extractor.parse_table(table)
                schedules.setdefault("schedule_i", []).extend(contributions)

        logger.debug(f"Routed tables to schedules: {list(schedules.keys())}")
        return schedules

    def _classify_table(self, table: Dict[str, Any]) -> Optional[str]:
        """Classify a table as belonging to a specific schedule.

        Args:
            table: Parsed table with headers and rows

        Returns:
            Schedule identifier (e.g., "schedule_a") or None if unclassified
        """
        headers = [h.lower() for h in table.get("headers", [])]
        header_text = " ".join(headers)

        # Schedule A: Assets
        if any(kw in header_text for kw in ["asset", "description", "value", "income type"]):
            return "schedule_a"

        # Schedule C: Earned Income
        if any(kw in header_text for kw in ["source", "salary", "honoraria", "employer"]):
            return "schedule_c"

        # Schedule D: Liabilities
        if any(kw in header_text for kw in ["creditor", "liability", "debt", "loan"]):
            return "schedule_d"

        # Schedule E: Positions
        if any(kw in header_text for kw in ["position", "organization", "title"]):
            return "schedule_e"

        # Schedule F: Agreements
        if any(kw in header_text for kw in ["agreement", "parties", "terms"]):
            return "schedule_f"

        # Schedule G: Gifts
        if any(kw in header_text for kw in ["gift", "donor", "source", "value"]) and "travel" not in header_text:
            return "schedule_g"

        # Schedule H: Travel
        if any(kw in header_text for kw in ["travel", "itinerary", "destination", "reimbursement"]):
            return "schedule_h"

        # Schedule I: Charity
        if any(kw in header_text for kw in ["charity", "honoraria", "payment to charity"]):
            return "schedule_i"

        return None

    def _extract_exclusions(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract Exclusions section (2 Yes/No questions).

        Questions:
        1. "Did you exclude from this report any other trust..."
        2. "Did you claim any exemption from reporting..."

        Args:
            blocks: Textract blocks
            block_map: Block ID to block mapping

        Returns:
            Exclusions dictionary with 'trusts' and 'exemption' keys
        """
        exclusions = {
            "qualified_blind_trust": None,  # Yes/No for trust question
            "claimed_exemption": None,      # Yes/No for exemption question
        }

        # Combine all text to search for exclusion section
        text_blocks = [b for b in blocks if b.get("BlockType") == "LINE"]

        for i, block in enumerate(text_blocks):
            text = block.get("Text", "").lower()

            # Look for qualified blind trust question
            if "qualified blind trust" in text or ("trust" in text and "exclude" in text):
                # Check next few blocks for Yes/No checkboxes
                for j in range(i, min(i + 5, len(text_blocks))):
                    nearby_text = text_blocks[j].get("Text", "").lower()
                    if "yes" in nearby_text and "no" in nearby_text:
                        # Try to determine which is checked (heuristic)
                        if nearby_text.index("yes") < nearby_text.index("no"):
                            # Check if "x" or checkmark near "yes"
                            if "x" in nearby_text[:nearby_text.index("no")]:
                                exclusions["qualified_blind_trust"] = "Yes"
                            else:
                                exclusions["qualified_blind_trust"] = "No"
                        break

            # Look for exemption question
            if "exemption" in text or ("claim" in text and "reporting" in text):
                # Check next few blocks for Yes/No
                for j in range(i, min(i + 5, len(text_blocks))):
                    nearby_text = text_blocks[j].get("Text", "").lower()
                    if "yes" in nearby_text and "no" in nearby_text:
                        # Heuristic to determine checked box
                        if nearby_text.index("yes") < nearby_text.index("no"):
                            if "x" in nearby_text[:nearby_text.index("no")]:
                                exclusions["claimed_exemption"] = "Yes"
                            else:
                                exclusions["claimed_exemption"] = "No"
                        break

        return exclusions

    def _extract_certification(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract certification information.

        Args:
            blocks: Textract blocks
            block_map: Block ID to block mapping

        Returns:
            Certification dictionary
        """
        certification = {
            "is_certified": False,
            "signature": None,
            "date": None
        }

        # Find certification text and signature
        for block in blocks:
            if block.get("BlockType") == "LINE":
                text = block.get("Text", "").strip()
                text_lower = text.lower()
                
                # Handle "Digitally Signed by" and "Digitally Signed:"
                if "digitally signed" in text_lower:
                    # Remove prefix
                    sig_text = re.sub(r'digitally signed\s*(by|:)?\s*', '', text, flags=re.IGNORECASE).strip()
                    
                    # Check for date in the same line (e.g. "Name , MM/DD/YYYY")
                    date_match = re.search(r',\s*(\d{1,2}/\d{1,2}/\d{4})', sig_text)
                    if date_match:
                        certification["date"] = date_match.group(1)
                        # Remove date from signature
                        sig_text = sig_text.replace(date_match.group(0), "").strip()
                    
                    certification["signature"] = sig_text
                    certification["is_certified"] = True

                elif "filed" in text_lower and "/" in text and not certification["date"]:
                     # Try to grab date if near signature or looks like filing date
                     # Format: Filed MM/DD/YYYY @ HH:MM PM
                     date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
                     if date_match:
                         certification["date"] = date_match.group(1)

        return certification

    def _extract_schedule_summary(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, bool]:
        """Extract 'None disclosed' status for each schedule.
        
        Returns:
            Dict of schedule_id -> has_disclosure (True if disclosed, False if 'None disclosed')
        """
        # Default to True (has disclosure)
        schedule_status = {
            "schedule_a": True,
            "schedule_b": True,
            "schedule_c": True,
            "schedule_d": True,
            "schedule_e": True,
            "schedule_f": True,
            "schedule_g": True,
            "schedule_h": True,
            "schedule_i": True
        }
        
        # Map of schedule headers to their keys
        # Based on PDF: "S A: ...", "S B: ...", etc.
        schedule_markers = {
            "schedule_a": ["s a:", "schedule a"],
            "schedule_b": ["s b:", "schedule b"],
            "schedule_c": ["s c:", "schedule c"],
            "schedule_d": ["s d:", "schedule d"],
            "schedule_e": ["s e:", "schedule e"],
            "schedule_f": ["s f:", "schedule f"],
            "schedule_g": ["s g:", "schedule g"],
            "schedule_h": ["s h:", "schedule h"],
            "schedule_i": ["s i:", "schedule i"]
        }

        # Iterate through blocks to find schedule headers and subsequent "None disclosed" text
        sorted_blocks = sorted(
            [b for b in blocks if b.get("BlockType") == "LINE"],
            key=lambda b: (b.get("Page", 1), b.get("Geometry", {}).get("BoundingBox", {}).get("Top", 0))
        )

        for i, block in enumerate(sorted_blocks):
            text = block.get("Text", "").lower()
            
            # Check if this block is a schedule header
            found_schedule = None
            for sched_key, markers in schedule_markers.items():
                if any(m in text for m in markers):
                    found_schedule = sched_key
                    break
            
            if found_schedule:
                # Look ahead at the next few blocks for "None disclosed"
                # usually it's the very next line
                for j in range(1, 5): # Check next 4 blocks
                    if i + j < len(sorted_blocks):
                        next_block = sorted_blocks[i+j]
                        # Ensure on same page
                        if next_block.get("Page") != block.get("Page"):
                            break
                            
                        next_text = next_block.get("Text", "").lower()
                        if "none disclosed" in next_text:
                            schedule_status[found_schedule] = False
                            break

        return schedule_status

    def _extract_key_value_pairs(
        self,
        blocks: List[Dict[str, Any]],
        block_map: Dict[str, Dict[str, Any]]
    ) -> Dict[str, str]:
        """Extract KEY_VALUE_SET blocks from Textract response.

        Args:
            blocks: Textract blocks
            block_map: Block ID to block mapping

        Returns:
            Dictionary of key to value strings
        """
        kv_pairs = {}

        for block in blocks:
            if block.get("BlockType") != "KEY_VALUE_SET":
                continue

            entity_types = block.get("EntityTypes", [])

            if "KEY" in entity_types:
                key_text = self._get_text_from_relationships(
                    block, block_map, "CHILD"
                )
                
                # Get VALUE block(s) first
                value_text = ""
                for relationship in block.get("Relationships", []):
                    if relationship.get("Type") == "VALUE":
                        for value_id in relationship.get("Ids", []):
                            if value_id in block_map:
                                value_block = block_map[value_id]
                                # Get text from VALUE block's children
                                value_text += self._get_text_from_relationships(
                                    value_block, block_map, "CHILD"
                                ) + " "

                if key_text:
                    kv_pairs[key_text.strip()] = value_text.strip()

        return kv_pairs

    def _get_text_from_relationships(
        self,
        block: Dict[str, Any],
        block_map: Dict[str, Dict[str, Any]],
        relationship_type: str
    ) -> str:
        """Get text from blocks referenced by relationships.

        Args:
            block: Source block
            block_map: Block ID to block mapping
            relationship_type: Type of relationship (e.g., "CHILD", "VALUE")

        Returns:
            Concatenated text from related blocks
        """
        text_parts = []

        for relationship in block.get("Relationships", []):
            if relationship.get("Type") == relationship_type:
                for block_id in relationship.get("Ids", []):
                    if block_id in block_map:
                        related_block = block_map[block_id]
                        if related_block.get("BlockType") == "WORD":
                            text_parts.append(related_block.get("Text", ""))

        return " ".join(text_parts)

    def _get_cell_text(
        self,
        cell_block: Dict[str, Any],
        block_map: Dict[str, Dict[str, Any]]
    ) -> str:
        """Get text content from a CELL block.

        Args:
            cell_block: CELL block from Textract
            block_map: Block ID to block mapping

        Returns:
            Cell text content
        """
        return self._get_text_from_relationships(cell_block, block_map, "CHILD")

    def _get_nearby_text(
        self,
        block: Dict[str, Any],
        blocks: List[Dict[str, Any]],
        distance_threshold: float = 0.05
    ) -> str:
        """Get text from blocks near a given block (useful for checkbox labels).

        Args:
            block: Reference block (e.g., checkbox)
            blocks: All blocks
            distance_threshold: Max distance to consider "nearby" (normalized 0-1)

        Returns:
            Concatenated nearby text
        """
        bbox = block.get("Geometry", {}).get("BoundingBox", {})
        page = block.get("Page", 1)

        if not bbox:
            return ""

        ref_y = bbox.get("Top", 0) + bbox.get("Height", 0) / 2

        nearby_texts = []
        for other_block in blocks:
            if (other_block.get("BlockType") == "LINE" and
                other_block.get("Page") == page):

                other_bbox = other_block.get("Geometry", {}).get("BoundingBox", {})
                if not other_bbox:
                    continue

                other_y = other_bbox.get("Top", 0) + other_bbox.get("Height", 0) / 2

                if abs(ref_y - other_y) < distance_threshold:
                    nearby_texts.append(other_block.get("Text", ""))

        return " ".join(nearby_texts)

    def _get_page_count(self, blocks: List[Dict[str, Any]]) -> int:
        """Get total number of pages from blocks.

        Args:
            blocks: Textract blocks

        Returns:
            Number of pages
        """
        if not blocks:
            return 0
        return max(block.get("Page", 1) for block in blocks)

    def _calculate_confidence(
        self,
        header: Dict[str, Any],
        part_i: Dict[str, Any],
        schedules: Dict[str, Any]
    ) -> float:
        """Calculate overall extraction confidence score.

        Args:
            header: Extracted header data
            part_i: Extracted Part I questions
            schedules: Extracted schedules

        Returns:
            Confidence score (0.0 to 1.0)
        """
        scores = []

        # Header completeness (30%)
        header_fields = [v for v in header.values() if v]
        header_score = len(header_fields) / max(len(header), 1)
        scores.append(header_score * 0.3)

        # Part I completeness (20%)
        part_i_answers = [v for v in part_i.values() if v is not None]
        part_i_score = len(part_i_answers) / max(len(part_i), 1)
        scores.append(part_i_score * 0.2)

        # Schedule presence (50%)
        expected_schedules = 4  # A, C, D, E are most common
        schedule_score = len(schedules) / expected_schedules
        scores.append(min(schedule_score, 1.0) * 0.5)

        return min(sum(scores), 1.0)
