"""Parser for ICD-10-CM neoplasm table XML file.

Parses ICD10CM.index (neoplasm table) XML into IndexEntryData objects,
capturing the matrix of neoplasm behavior codes mapped to column headings.
"""

from __future__ import annotations

import logging
from pathlib import Path

from lxml import etree

from app.ingestion.parsers.index import (
    IndexEntryData,
    _extract_title_text,
    _get_nemod,
    _get_text,
)

logger = logging.getLogger(__name__)


class NeoplasmParser:
    """Parses the ICD-10-CM neoplasm table XML file.

    XML structure:
        ICD10CM.index > indexHeading (column definitions) > letter > mainTerm

    Column mapping (from indexHeading):
        col 1: Neoplasm (the title/site)
        col 2: Malignant Primary
        col 3: Malignant Secondary
        col 4: Ca in situ
        col 5: Benign
        col 6: Uncertain Behavior
        col 7: Unspecified Behavior
    """

    def __init__(self) -> None:
        self.column_headings: dict[str, str] = {}

    def parse(self, file_path: str | Path) -> list[IndexEntryData]:
        """Parse the neoplasm table XML file.

        Args:
            file_path: Path to the icd10cm-neoplasm-*-XML.xml file.

        Returns:
            List of IndexEntryData with matrix_codes for each neoplasm site.
        """
        file_path = Path(file_path)
        logger.info("Parsing neoplasm table XML: %s", file_path)

        tree = etree.parse(str(file_path))  # noqa: S320
        root = tree.getroot()

        # Parse column headings from indexHeading
        self._parse_headings(root)

        entries: list[IndexEntryData] = []
        letters = root.findall("letter")
        logger.info("Found %d letter sections in neoplasm table", len(letters))

        for letter_el in letters:
            for main_term_el in letter_el.findall("mainTerm"):
                self._parse_term(
                    term_el=main_term_el,
                    parent_term=None,
                    level=0,
                    entries=entries,
                )

        logger.info("Parsed %d neoplasm index entries", len(entries))
        return entries

    def _parse_headings(self, root: etree._Element) -> None:
        """Parse the indexHeading element to get column name mappings."""
        heading_el = root.find("indexHeading")
        if heading_el is None:
            logger.warning("No indexHeading found in neoplasm table XML")
            return

        for head_el in heading_el.findall("head"):
            col = head_el.get("col", "")
            text = head_el.text or ""
            self.column_headings[col] = text.strip()

        logger.info("Neoplasm table columns: %s", self.column_headings)

    def _parse_term(
        self,
        term_el: etree._Element,
        parent_term: str | None,
        level: int,
        entries: list[IndexEntryData],
    ) -> None:
        """Recursively parse a mainTerm or term element from the neoplasm table."""
        title_el = term_el.find("title")
        if title_el is None:
            return

        term_text = _extract_title_text(title_el)
        if not term_text:
            return

        nemod = _get_nemod(term_el)
        see_ref = _get_text(term_el, "see")
        see_also_ref = _get_text(term_el, "seeAlso")

        # Extract cell values (codes mapped to column headings)
        matrix_codes: dict[str, str] = {}
        for cell_el in term_el.findall("cell"):
            col = cell_el.get("col", "")
            code_text = (cell_el.text or "").strip()
            # Skip placeholder values like "--" or "-"
            if code_text and code_text not in ("--", "-"):
                col_name = self.column_headings.get(col, f"col_{col}")
                matrix_codes[col_name] = code_text

        entry = IndexEntryData(
            term=term_text,
            parent_term=parent_term,
            level=level,
            code=None,  # Neoplasm entries use matrix_codes instead
            see_reference=see_ref,
            see_also_reference=see_also_ref,
            index_type="neoplasm",
            matrix_codes=matrix_codes,
            nemod=nemod,
        )
        entries.append(entry)

        # Recurse into child term elements
        for child_term_el in term_el.findall("term"):
            self._parse_term(
                term_el=child_term_el,
                parent_term=term_text,
                level=level + 1,
                entries=entries,
            )
