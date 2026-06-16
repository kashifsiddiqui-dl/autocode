"""Parser for ICD-10-CM tabular (hierarchical diagnosis codes) XML file.

Parses ICD10CM.tabular XML into structured IcdCodeData objects, preserving
the full hierarchy of chapters > sections > diag elements with all annotations.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)


@dataclass
class IcdCodeData:
    """Represents a single ICD-10-CM diagnosis code with full metadata."""

    code: str
    description: str
    short_description: str
    parent_code: str | None
    is_billable: bool
    chapter_num: str
    chapter_name: str
    section_id: str
    section_name: str
    code_level: int  # 0=category (3-char), 1=subcategory, 2=code, etc.
    inclusion_terms: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    excludes1: list[str] = field(default_factory=list)
    excludes2: list[str] = field(default_factory=list)
    code_first: list[str] = field(default_factory=list)
    use_additional_code: list[str] = field(default_factory=list)
    code_also: list[str] = field(default_factory=list)
    seven_chr_note: str | None = None
    seven_chr_def: list[dict[str, str]] = field(default_factory=list)


def _collect_notes(element: etree._Element, tag: str) -> list[str]:
    """Extract all <note> text values from a child element with the given tag."""
    container = element.find(tag)
    if container is None:
        return []
    notes = []
    for note_el in container.findall("note"):
        text = note_el.text
        if text:
            notes.append(text.strip())
    return notes


def _get_text(element: etree._Element, tag: str) -> str | None:
    """Get text content of a direct child element."""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _get_inner_text(element: etree._Element) -> str:
    """Get all text content of an element including tail text of children."""
    return (element.text or "") + "".join(
        (child.text or "") + (child.tail or "") for child in element
    )


class TabularParser:
    """Parses the ICD-10-CM tabular XML file into structured code data.

    The XML structure is:
        ICD10CM.tabular > chapter > section > diag (nested)

    Each diag can contain nested diag children, forming a code hierarchy.
    Annotations (excludes, includes, etc.) are inherited from parent elements.
    """

    def parse(self, file_path: str | Path) -> list[IcdCodeData]:
        """Parse the tabular XML file and return all diagnosis codes.

        Args:
            file_path: Path to the icd10c-tabular-*.xml file.

        Returns:
            List of IcdCodeData objects for every code in the tabular list.
        """
        file_path = Path(file_path)
        logger.info("Parsing tabular XML: %s", file_path)

        tree = etree.parse(str(file_path))  # noqa: S320
        root = tree.getroot()

        codes: list[IcdCodeData] = []
        chapters = root.findall("chapter")
        logger.info("Found %d chapters", len(chapters))

        for chapter_el in chapters:
            chapter_num = _get_text(chapter_el, "name") or ""
            chapter_desc = _get_text(chapter_el, "desc") or ""

            # Collect chapter-level annotations for inheritance
            chapter_excludes1 = _collect_notes(chapter_el, "excludes1")
            chapter_excludes2 = _collect_notes(chapter_el, "excludes2")
            chapter_includes = _collect_notes(chapter_el, "includes")
            chapter_use_additional = _collect_notes(chapter_el, "useAdditionalCode")
            chapter_code_first = _collect_notes(chapter_el, "codeFirst")

            for section_el in chapter_el.findall("section"):
                section_id = section_el.get("id", "")
                section_desc = _get_text(section_el, "desc") or ""

                # Collect section-level annotations for inheritance
                section_excludes1 = _collect_notes(section_el, "excludes1")
                section_excludes2 = _collect_notes(section_el, "excludes2")
                section_includes = _collect_notes(section_el, "includes")
                section_use_additional = _collect_notes(section_el, "useAdditionalCode")
                section_code_first = _collect_notes(section_el, "codeFirst")
                section_code_also = _collect_notes(section_el, "codeAlso")

                inherited = _InheritedAnnotations(
                    excludes1=chapter_excludes1 + section_excludes1,
                    excludes2=chapter_excludes2 + section_excludes2,
                    includes=chapter_includes + section_includes,
                    use_additional_code=chapter_use_additional + section_use_additional,
                    code_first=chapter_code_first + section_code_first,
                    code_also=section_code_also,
                )

                for diag_el in section_el.findall("diag"):
                    self._parse_diag(
                        diag_el=diag_el,
                        parent_code=None,
                        chapter_num=chapter_num,
                        chapter_name=chapter_desc,
                        section_id=section_id,
                        section_name=section_desc,
                        level=0,
                        inherited=inherited,
                        codes=codes,
                    )

        logger.info("Parsed %d total codes from tabular XML", len(codes))
        return codes

    def _parse_diag(
        self,
        diag_el: etree._Element,
        parent_code: str | None,
        chapter_num: str,
        chapter_name: str,
        section_id: str,
        section_name: str,
        level: int,
        inherited: _InheritedAnnotations,
        codes: list[IcdCodeData],
    ) -> None:
        """Recursively parse a <diag> element and its children."""
        code = _get_text(diag_el, "name") or ""
        desc = _get_text(diag_el, "desc") or ""

        # Determine billable: a code is billable if it has no child <diag> elements
        child_diags = diag_el.findall("diag")
        is_billable = len(child_diags) == 0

        # Collect own annotations
        own_inclusion_terms = _collect_notes(diag_el, "inclusionTerm")
        own_includes = _collect_notes(diag_el, "includes")
        own_excludes1 = _collect_notes(diag_el, "excludes1")
        own_excludes2 = _collect_notes(diag_el, "excludes2")
        own_code_first = _collect_notes(diag_el, "codeFirst")
        own_use_additional = _collect_notes(diag_el, "useAdditionalCode")
        own_code_also = _collect_notes(diag_el, "codeAlso")

        # 7th character annotations
        seven_chr_note_text: str | None = None
        seven_chr_note_el = diag_el.find("sevenChrNote")
        if seven_chr_note_el is not None:
            note_el = seven_chr_note_el.find("note")
            if note_el is not None and note_el.text:
                seven_chr_note_text = note_el.text.strip()

        seven_chr_def_list: list[dict[str, str]] = []
        seven_chr_def_el = diag_el.find("sevenChrDef")
        if seven_chr_def_el is not None:
            for ext_el in seven_chr_def_el.findall("extension"):
                char = ext_el.get("char", "")
                desc_text = ext_el.text or ""
                seven_chr_def_list.append({"char": char, "description": desc_text.strip()})

        # Build short description (first 60 chars)
        short_desc = desc[:60] if len(desc) > 60 else desc

        # Merge inherited with own annotations
        merged_excludes1 = inherited.excludes1 + own_excludes1
        merged_excludes2 = inherited.excludes2 + own_excludes2

        icd_code = IcdCodeData(
            code=code,
            description=desc,
            short_description=short_desc,
            parent_code=parent_code,
            is_billable=is_billable,
            chapter_num=chapter_num,
            chapter_name=chapter_name,
            section_id=section_id,
            section_name=section_name,
            code_level=level,
            inclusion_terms=own_inclusion_terms,
            includes=inherited.includes + own_includes,
            excludes1=merged_excludes1,
            excludes2=merged_excludes2,
            code_first=inherited.code_first + own_code_first,
            use_additional_code=inherited.use_additional_code + own_use_additional,
            code_also=inherited.code_also + own_code_also,
            seven_chr_note=seven_chr_note_text,
            seven_chr_def=seven_chr_def_list,
        )
        codes.append(icd_code)

        # Build inherited annotations for children: pass down own + inherited
        child_inherited = _InheritedAnnotations(
            excludes1=merged_excludes1,
            excludes2=merged_excludes2,
            includes=inherited.includes + own_includes,
            use_additional_code=inherited.use_additional_code + own_use_additional,
            code_first=inherited.code_first + own_code_first,
            code_also=inherited.code_also + own_code_also,
            # Inherit 7th character definitions downward if children don't override
            seven_chr_note=seven_chr_note_text or inherited.seven_chr_note,
            seven_chr_def=seven_chr_def_list or inherited.seven_chr_def,
        )

        # Recurse into child diag elements
        for child_diag_el in child_diags:
            # Inherit 7th char from parent if child doesn't have its own
            self._parse_diag(
                diag_el=child_diag_el,
                parent_code=code,
                chapter_num=chapter_num,
                chapter_name=chapter_name,
                section_id=section_id,
                section_name=section_name,
                level=level + 1,
                inherited=child_inherited,
                codes=codes,
            )


@dataclass
class _InheritedAnnotations:
    """Annotations inherited from parent chapter/section/diag elements."""

    excludes1: list[str] = field(default_factory=list)
    excludes2: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    use_additional_code: list[str] = field(default_factory=list)
    code_first: list[str] = field(default_factory=list)
    code_also: list[str] = field(default_factory=list)
    seven_chr_note: str | None = None
    seven_chr_def: list[dict[str, str]] = field(default_factory=list)
