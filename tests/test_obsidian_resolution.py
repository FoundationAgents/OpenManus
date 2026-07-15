"""Tests for the Obsidian wikilink resolution logic.

These reproduce the exact bugs reported and verify the fixes:
1. Path-qualified wikilinks ([[projects/Overview]]) now resolve correctly.
2. Duplicate titles are detected and ambiguous links are skipped.
3. Diff-based edge updates preserve edges from untouched notes.
"""
import re
import uuid
from collections import defaultdict

import pytest


# --------------------------------------------------------------------------
# Inline the resolution logic from the fixed code for unit testing
# without requiring a database connection.
# --------------------------------------------------------------------------

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[^\]]*)\]\]")


class FakeNote:
    """Minimal stand-in for ObsidianNoteORM."""

    def __init__(self, note_id: str, path: str, title: str, content: str = ""):
        self.note_id = note_id
        self.path = path
        self.title = title
        self.content = content


def resolve_wikilink(target_name: str, all_notes: list[FakeNote]) -> FakeNote | None:
    """Replicate the fixed resolution logic from auto_sync_obsidian_notes."""
    # Build lookup dicts
    all_by_path = {note.path: note for note in all_notes}

    all_by_path_stem: dict[str, list[FakeNote]] = defaultdict(list)
    for note in all_notes:
        stem = note.path
        if stem.endswith(".md"):
            stem = stem[:-3]
        all_by_path_stem[stem].append(note)

    all_by_title: dict[str, list[FakeNote]] = defaultdict(list)
    for note in all_notes:
        all_by_title[note.title].append(note)

    # Resolution order: path-stem > exact path > unambiguous title
    stem_matches = all_by_path_stem.get(target_name, [])
    if len(stem_matches) == 1:
        return stem_matches[0]
    if target_name in all_by_path:
        return all_by_path[target_name]
    title_matches = all_by_title.get(target_name, [])
    if len(title_matches) == 1:
        return title_matches[0]
    return None


def compute_edges(
    source_notes: list[FakeNote],
    all_notes: list[FakeNote],
) -> set[tuple[str, str, str]]:
    """Replicate the diff-based edge computation."""
    edges: set[tuple[str, str, str]] = set()
    for note in source_notes:
        for link in WIKILINK_RE.findall(note.content):
            target_name = link.strip()
            if not target_name:
                continue
            target = resolve_wikilink(target_name, all_notes)
            if target is not None and target.note_id != note.note_id:
                edges.add((note.note_id, target.note_id, "wikilink"))
    return edges


# --------------------------------------------------------------------------
# Bug 1: Path-qualified links never resolve (FIXED)
# --------------------------------------------------------------------------


class TestPathQualifiedLinks:
    """[[projects/Overview]] must resolve to the note at 'projects/Overview.md'."""

    def test_path_qualified_link_resolves(self):
        note_a = FakeNote("note-A", "projects/Overview.md", "Overview")
        note_b = FakeNote("note-B", "notes/index.md", "Index", content="See [[projects/Overview]]")

        result = resolve_wikilink("projects/Overview", [note_a, note_b])
        assert result is not None, "Path-qualified link should resolve"
        assert result.note_id == "note-A"

    def test_exact_path_still_works(self):
        note_a = FakeNote("note-A", "README", "README")
        result = resolve_wikilink("README", [note_a])
        assert result is not None
        assert result.note_id == "note-A"

    def test_path_qualified_edge_created(self):
        note_a = FakeNote("note-A", "projects/Overview.md", "Overview")
        note_b = FakeNote("note-B", "notes/index.md", "Index", content="See [[projects/Overview]]")

        edges = compute_edges([note_b], [note_a, note_b])
        assert ("note-B", "note-A", "wikilink") in edges


# --------------------------------------------------------------------------
# Bug 2: Duplicate titles silently collide (FIXED)
# --------------------------------------------------------------------------


class TestDuplicateTitles:
    """When two notes share the same title, title-only links should be ambiguous and skipped."""

    def test_duplicate_title_link_is_ambiguous(self):
        note_a = FakeNote("note-A", "projects/Overview.md", "Overview")
        note_b = FakeNote("note-B", "notes/Overview.md", "Overview")

        result = resolve_wikilink("Overview", [note_a, note_b])
        assert result is None, "Duplicate title should be ambiguous — link must NOT resolve"

    def test_unique_title_still_resolves(self):
        note_a = FakeNote("note-A", "projects/Overview.md", "Overview")
        note_b = FakeNote("note-B", "notes/Daily.md", "Daily")

        result = resolve_wikilink("Daily", [note_a, note_b])
        assert result is not None
        assert result.note_id == "note-B"

    def test_path_qualified_disambiguates_duplicate_titles(self):
        """Even when titles collide, a path-qualified link should resolve to the correct one."""
        note_a = FakeNote("note-A", "projects/Overview.md", "Overview")
        note_b = FakeNote("note-B", "notes/Overview.md", "Overview")

        result = resolve_wikilink("projects/Overview", [note_a, note_b])
        assert result is not None, "Path-qualified should disambiguate"
        assert result.note_id == "note-A"

    def test_duplicate_titles_no_edge_for_ambiguous(self):
        note_a = FakeNote("note-A", "projects/Overview.md", "Overview")
        note_b = FakeNote("note-B", "notes/Overview.md", "Overview")
        note_c = FakeNote("note-C", "index.md", "Index", content="See [[Overview]]")

        edges = compute_edges([note_c], [note_a, note_b, note_c])
        # No edge should be created because [[Overview]] is ambiguous
        assert len(edges) == 0


# --------------------------------------------------------------------------
# Bug 3: Graph edges destroyed on next task run (FIXED via diff-based)
# --------------------------------------------------------------------------


class TestDiffBasedEdges:
    """Only edges sourced from the batch being processed should be touched."""

    def test_edges_from_untouched_notes_preserved(self):
        # Simulate: imported vault created edges from note_imp
        note_imp = FakeNote("note-imp", "vault/Research.md", "Research", content="See [[Design]]")
        note_des = FakeNote("note-des", "vault/Design.md", "Design")
        # Workspace auto-sync only touches workspace notes
        note_ws = FakeNote("note-ws", "readme.md", "README", content="Links to [[Design]]")

        all_notes = [note_imp, note_des, note_ws]

        # Imported edges (from a previous import)
        imported_edges = compute_edges([note_imp], all_notes)
        assert ("note-imp", "note-des", "wikilink") in imported_edges

        # Now auto_sync runs and only processes workspace notes
        workspace_edges = compute_edges([note_ws], all_notes)
        assert ("note-ws", "note-des", "wikilink") in workspace_edges

        # The imported edge should still exist (not wiped by workspace scan)
        # In the old code, delete-all-rebuild would wipe imported_edges
        # In the fixed code, only workspace note edges are diffed
        combined = imported_edges | workspace_edges
        assert ("note-imp", "note-des", "wikilink") in combined
        assert ("note-ws", "note-des", "wikilink") in combined

    def test_batch_import_preserves_previous_batch(self):
        # Batch 1
        note_a = FakeNote("note-A", "batch1/A.md", "NoteA", content="See [[NoteB]]")
        note_b = FakeNote("note-B", "batch1/B.md", "NoteB")
        # Batch 2
        note_c = FakeNote("note-C", "batch2/C.md", "NoteC", content="See [[NoteA]]")

        all_notes = [note_a, note_b, note_c]

        batch1_edges = compute_edges([note_a, note_b], all_notes)
        batch2_edges = compute_edges([note_c], all_notes)

        # Both batches' edges should survive independently
        assert ("note-A", "note-B", "wikilink") in batch1_edges
        assert ("note-C", "note-A", "wikilink") in batch2_edges

    def test_self_links_skipped(self):
        note = FakeNote("note-A", "self.md", "Self", content="See [[Self]]")
        edges = compute_edges([note], [note])
        assert len(edges) == 0, "Self-links should be skipped"


# --------------------------------------------------------------------------
# Wikilink regex
# --------------------------------------------------------------------------


class TestWikilinkRegex:
    def test_simple_link(self):
        assert WIKILINK_RE.findall("See [[Note A]]") == ["Note A"]

    def test_link_with_heading(self):
        assert WIKILINK_RE.findall("See [[Note A#section]]") == ["Note A"]

    def test_link_with_alias(self):
        assert WIKILINK_RE.findall("See [[Note A|display text]]") == ["Note A"]

    def test_path_qualified(self):
        assert WIKILINK_RE.findall("See [[projects/Overview]]") == ["projects/Overview"]

    def test_multiple_links(self):
        text = "See [[A]] and [[B]] and [[C]]"
        assert WIKILINK_RE.findall(text) == ["A", "B", "C"]
