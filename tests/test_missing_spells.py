import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build"))
import missing_spells


class TempManifest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self._orig = missing_spells.PATH
        missing_spells.PATH = os.path.join(self._dir.name, "missing-spells.json")

    def tearDown(self):
        missing_spells.PATH = self._orig
        self._dir.cleanup()


class TestSkeleton(TempManifest):
    def test_load_returns_skeleton_when_absent(self):
        d = missing_spells.load()
        self.assertEqual(d["version"], missing_spells.MANIFEST_VERSION)
        self.assertEqual(d["monsters"], {})
        self.assertEqual(d["spellLists"], {})
        self.assertEqual(d["aliases"], {})

    def test_save_then_load_roundtrips(self):
        missing_spells.set_monsters({"abc": {"name": "Ghoul", "pack": "monsters", "spells": []}})
        self.assertEqual(missing_spells.load()["monsters"]["abc"]["name"], "Ghoul")

    def test_save_is_deterministic_and_newline_terminated(self):
        missing_spells.set_aliases({"b": "2", "a": "1"})
        first = open(missing_spells.PATH, encoding="utf-8").read()
        missing_spells.set_aliases({"a": "1", "b": "2"})
        second = open(missing_spells.PATH, encoding="utf-8").read()
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("\n"))
        self.assertLess(first.index('"a"'), first.index('"b"'))


class TestSectionIsolation(TempManifest):
    def test_set_monsters_replaces_whole_section(self):
        missing_spells.set_monsters({"a": {"name": "A", "pack": "monsters", "spells": []}})
        missing_spells.set_monsters({"b": {"name": "B", "pack": "monsters", "spells": []}})
        self.assertEqual(sorted(missing_spells.load()["monsters"]), ["b"])

    def test_set_spell_lists_preserves_the_other_journal(self):
        missing_spells.set_spell_lists("JCLASS", {
            "JCLASS.p1": {"name": "Mage Spells", "identifier": "wc5e-mage",
                          "pack": "spell-lists", "spells": []}})
        missing_spells.set_spell_lists("JSUB", {
            "JSUB.p9": {"name": "Study of Destruction Spells", "identifier": "sub",
                        "pack": "spell-lists", "spells": []}})
        keys = sorted(missing_spells.load()["spellLists"])
        self.assertEqual(keys, ["JCLASS.p1", "JSUB.p9"])

    def test_set_spell_lists_replaces_only_its_own_journal(self):
        missing_spells.set_spell_lists("JCLASS", {"JCLASS.p1": {"name": "one", "identifier": "i",
                                                                "pack": "spell-lists", "spells": []}})
        missing_spells.set_spell_lists("JSUB", {"JSUB.p9": {"name": "keep", "identifier": "i",
                                                            "pack": "spell-lists", "spells": []}})
        missing_spells.set_spell_lists("JCLASS", {"JCLASS.p2": {"name": "two", "identifier": "i",
                                                                "pack": "spell-lists", "spells": []}})
        keys = sorted(missing_spells.load()["spellLists"])
        self.assertEqual(keys, ["JCLASS.p2", "JSUB.p9"])

    def test_prefix_match_is_on_the_dot_boundary(self):
        """A journal id that is a prefix of another must not be clobbered."""
        missing_spells.set_spell_lists("JA", {"JA.p1": {"name": "a", "identifier": "i",
                                                        "pack": "spell-lists", "spells": []}})
        missing_spells.set_spell_lists("JAB", {"JAB.p1": {"name": "b", "identifier": "i",
                                                          "pack": "spell-lists", "spells": []}})
        missing_spells.set_spell_lists("JAB", {"JAB.p2": {"name": "b2", "identifier": "i",
                                                          "pack": "spell-lists", "spells": []}})
        self.assertEqual(sorted(missing_spells.load()["spellLists"]), ["JA.p1", "JAB.p2"])


if __name__ == "__main__":
    unittest.main()
