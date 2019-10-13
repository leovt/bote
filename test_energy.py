import unittest

from energy import *

class TestEnergy(unittest.TestCase):
    def test_representations(self):
        self.assertEqual(str(ZERO), '{0}')
        self.assertEqual(str(COLORLESS), '{1}')
        self.assertEqual(str(RED), '{R}')
        self.assertEqual(str(GREEN), '{G}')
        self.assertEqual(str(BLUE), '{B}')
        self.assertEqual(str(WHITE), '{W}')
        self.assertEqual(str(YELLOW), '{Y}')
        self.assertEqual(str(BLUE + 2 * YELLOW), '{Y}{Y}{B}')

    def test_parse(self):
        self.assertEqual(Energy.parse('{1}{R}{R}'), 2*RED+COLORLESS)

    def test_pool_enough(self):
        energy_pool = EnergyPool()
        energy_pool.add(2*RED + 4*GREEN)
        self.assertTrue(energy_pool.can_pay(4*COLORLESS + 2*RED))
        energy_pool.pay(2*RED + COLORLESS)
        self.assertEqual(energy_pool.energy.total, 3)

    def test_pool_lacking(self):
        energy_pool = EnergyPool()
        energy_pool.add(RED)
        self.assertFalse(energy_pool.can_pay(1*COLORLESS + 2*RED))
