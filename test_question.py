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
        question = DeclareAttackers(player, [object()])
        self.assertTrue(question.validate(player, []))
        self.assertFalse(question.validate(object(), []))
        self.assertFalse(question.validate(player, [1]))
        self.assertTrue(question.validate(player, [0]))
        self.assertFalse(question.validate(player, [0, 1]))
        self.assertFalse(question.validate(player, [0, 0]))

    def test_validate_multiple_candidates(self):
        player = object()
        question = DeclareAttackers(player, [object(), object(), object()])
        self.assertTrue(question.validate(player, []))
        self.assertFalse(question.validate(object(), []))
        self.assertFalse(question.validate(player, [3]))
        self.assertTrue(question.validate(player, [0]))
        self.assertTrue(question.validate(player, [0, 1]))
        self.assertFalse(question.validate(player, [0, 0]))
        self.assertTrue(question.validate(player, [2]))
        self.assertTrue(question.validate(player, [2, 0]))
        self.assertFalse(question.validate(player, [2, 0, 1, 2]))


class TestDeclareBlockers(unittest.TestCase):
    def test_validate_multiple(self):
        player = object()
        question = DeclareBlockers(player, [
            {'candidate': 'alpha', 'attackers': [10,20,30]},
            {'candidate': 'beta',  'attackers': [10,20]},
            {'candidate': 'gamma', 'attackers': [30]}])

        self.assertTrue(question.validate(player, {0:0}))
        self.assertTrue(question.validate(player, {0:0, 1:0, 2:0}))
        self.assertTrue(question.validate(player, {0:2, 1:1, 2:0}))
        self.assertFalse(question.validate(player, {2:1}))
