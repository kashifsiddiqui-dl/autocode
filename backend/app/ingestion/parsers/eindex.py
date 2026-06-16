"""Parser for ICD-10-CM external causes index XML file.

Parses ICD10CM.index (external causes) XML into IndexEntryData objects.
Similar structure to the disease index but with index_type="eindex".
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


class EIndexParser:
    """Parses the ICD-10-CM external causes index XML file.

    XML structure:
        ICD10CM.index > letter > mainTerm (with nested term children)

    Each mainTerm/term has: title, and optional: code, subcat, see, seeAlso,
    nemod, and nested term children. The <subcat> element is used in the
    external causes index as an alternative to <code>.
    """

    def parse(self, file_path: str | Path) -> list[IndexEntryData]:
        """Parse the external causes index XML file.

        Args:
            file_path: Path to the icd10cm-eindex-*-XML.xml file.

        Returns:
            List of IndexEntryData with index_type="eindex".
        """
        file_path = Path(file_path)
        logger.info("Parsing external causes index XML: %s", file_path)

        tree = etree.parse(str(file_path))  # noqa: S320
        root = tree.getroot()

        entries: list[IndexEntryData] = []
        letters = root.findall("letter")
        logger.info("Found %d letter sections in external causes index", len(letters))

        for letter_el in letters:
            for main_term_el in letter_el.findall("mainTerm"):
                self._parse_term(
                    term_el=main_term_el,
                    parent_term=None,
                    level=0,
                    entries=entries,
                )

        logger.info("Parsed %d external cause index entries", len(entries))
        return entries

    def _parse_term(
        self,
        term_el: etree._Element,
        parent_term: str | None,
        level: int,
        entries: list[IndexEntryData],
    ) -> None:
        """Recursively parse a mainTerm or term element."""
        title_el = term_el.find("title")
        if title_el is None:
            return

        term_text = _extract_title_text(title_el)
        if not term_text:
            return

        # External causes index uses both <code> and <subcat> elements
        code = _get_text(term_el, "code")
        if code is None:
            code = _get_text(term_el, "subcat")

        see_ref = _get_text(term_el, "see")
        see_also_ref = _get_text(term_el, "seeAlso")
        nemod = _get_nemod(term_el)

        entry = IndexEntryData(
            term=term_text,
            parent_term=parent_term,
            level=level,
            code=code,
            see_reference=see_ref,
            see_also_reference=see_also_ref,
            index_type="eindex",
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
