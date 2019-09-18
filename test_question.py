import unittest

from question import DeclareAttackers, DeclareBlockers

class TestDeclareAttackers(unittest.TestCase):
    def test_validate_no_candidates(self):
        player = object()
        question = DeclareAttackers(player, [])
        self.assertTrue(question.validate(player, []))
        self.assertFalse(question.validate(object(), []))
        self.assertFalse(question.validate(player, [1]))

    def test_validate_single_candidate(self):
        player = object()
        key = 'sdkcjp'
        question = DeclareAttackers(player, {key: 'attacker'})
        self.assertTrue(question.validate(player, []))
        self.assertFalse(question.validate(object(), []))
        self.assertFalse(question.validate(player, [1]))
        self.assertTrue(question.validate(player, [key]))
        self.assertFalse(question.validate(player, [key, 1]))
        self.assertFalse(question.validate(player, [key, key]))

    def test_validate_multiple_candidates(self):
        player = object()
        key1, key2, key3 = keys = 'jfasj', 'oaidf', 'odifo'
        question = DeclareAttackers(player, dict.fromkeys(keys))
        self.assertTrue(question.validate(player, []))
        self.assertFalse(question.validate(object(), []))
        self.assertFalse(question.validate(player, ['dposp']))
        self.assertTrue(question.validate(player, [key1]))
        self.assertTrue(question.validate(player, [key1, key2]))
        self.assertFalse(question.validate(player, [key1, key1]))
        self.assertTrue(question.validate(player, [key2]))
        self.assertTrue(question.validate(player, [key3, key1]))
        self.assertFalse(question.validate(player, [key3, key2, key1, key3]))


class TestDeclareBlockers(unittest.TestCase):
    def test_validate_multiple(self):
        player = object()
        question = DeclareBlockers(player, {
            'A': {'candidate': 'alpha', 'attackers': {'a': 10, 'b': 20, 'c': 30}},
            'B': {'candidate': 'beta',  'attackers': {'a': 10, 'b': 20}},
            'C': {'candidate': 'gamma', 'attackers': {'c': 30}}})

        self.assertTrue(question.validate(player, {'A': 'a'}))
        self.assertTrue(question.validate(player, {'A': 'a', 'B': 'a', 'C': 'c'}))
        self.assertTrue(question.validate(player, {'A': 'c', 'B': 'b', 'C': 'c'}))
        self.assertFalse(question.validate(player, {'C': 'a'}))
