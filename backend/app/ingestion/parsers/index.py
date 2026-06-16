"""Parser for ICD-10-CM disease index XML file.

Parses ICD10CM.index XML (disease index) into structured IndexEntryData objects,
capturing the hierarchical term structure with see/seeAlso cross-references.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)


@dataclass
class IndexEntryData:
    """Represents a single index entry (disease, drug, neoplasm, or external cause)."""

    term: str
    parent_term: str | None
    level: int
    code: str | None
    see_reference: str | None
    see_also_reference: str | None
    index_type: str = "disease"
    # For drug/neoplasm matrix entries
    matrix_codes: dict[str, str] = field(default_factory=dict)
    nemod: str | None = None  # non-essential modifier


def _extract_title_text(element: etree._Element) -> str:
    """Extract full text from a title element, including nested nemod elements.

    The title may contain inline <nemod> elements like:
        <title>Abasia<nemod>(-astasia) (hysterical)</nemod></title>
    We concatenate all text and tail parts to get the complete term.
    """
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


def _get_nemod(element: etree._Element) -> str | None:
    """Extract the nemod (non-essential modifier) from a title element."""
    title_el = element.find("title")
    if title_el is None:
        return None
    nemod_el = title_el.find("nemod")
    if nemod_el is not None and nemod_el.text:
        return nemod_el.text.strip()
    return None


def _get_text(element: etree._Element, tag: str) -> str | None:
    """Get text content of a direct child element, including nested text."""
    child = element.find(tag)
    if child is None:
        return None
    # Some elements like <see> or <seeAlso> may contain plain text
    text = child.text
    if text:
        return text.strip()
    return None


class IndexParser:
    """Parses the ICD-10-CM disease index XML file.

    XML structure:
        ICD10CM.index > letter > mainTerm (with nested term children)

    Each mainTerm/term has: title, and optional: code, see, seeAlso, nemod,
    and nested term children.
    """

    def parse(self, file_path: str | Path) -> list[IndexEntryData]:
        """Parse the disease index XML file.

        Args:
            file_path: Path to the icd10cm-index-*-XML.xml file.

        Returns:
            List of IndexEntryData for all index terms.
        """
        file_path = Path(file_path)
        logger.info("Parsing disease index XML: %s", file_path)

        tree = etree.parse(str(file_path))  # noqa: S320
        root = tree.getroot()

        entries: list[IndexEntryData] = []
        letters = root.findall("letter")
        logger.info("Found %d letter sections", len(letters))

        for letter_el in letters:
            for main_term_el in letter_el.findall("mainTerm"):
                self._parse_term(
                    term_el=main_term_el,
                    parent_term=None,
                    level=0,
                    entries=entries,
                    is_main=True,
                )

        logger.info("Parsed %d index entries", len(entries))
        return entries

    def _parse_term(
        self,
        term_el: etree._Element,
        parent_term: str | None,
        level: int,
        entries: list[IndexEntryData],
        is_main: bool = False,
    ) -> None:
        """Recursively parse a mainTerm or term element."""
        title_el = term_el.find("title")
        if title_el is None:
            return

        term_text = _extract_title_text(title_el)
        if not term_text:
            return

        code = _get_text(term_el, "code")
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
            index_type="disease",
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
