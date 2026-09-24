"""Tests unitarios de safety (sin hardware)."""
import os
import unittest

from agent import context, safety
from agent.context import reload


class SafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('ROS_AGENT_ROBOT', 'open_manipulator_omx_f')
        reload()

    def test_clamp_joint2_low(self):
        q = [0, -3.0, 0, 0, 0]
        out, noted = safety.clamp_joints(q)
        self.assertGreater(out[1], -2.1)
        self.assertTrue(noted)

    def test_format_ok(self):
        want = [0.0, 0.0, 0.0, 0.0, 0.0]
        after = [0.05, -0.02, 0.0, 0.0, 0.0]
        msg = safety.format_move_verification('move_arm_joints', want, after)
        self.assertIn('ok', msg)

    def test_format_fail_joint4(self):
        want = [0.0, -1.57, 1.57, 1.57, 0.0]
        after = [0.0, -1.57, 1.57, 0.2, 0.0]
        msg = safety.format_move_verification('go_home', want, after)
        self.assertIn('joint4', msg)

    def test_max_step_reject(self):
        os.environ['ROS_AGENT_MAX_STEP'] = '0.5'
        err = safety.check_max_step([0] * 5, [0.6, 0, 0, 0, 0])
        self.assertIsNotNone(err)
        self.assertIn('Rechazado', err)

    def test_profile_loaded(self):
        p = context.get_profile()
        self.assertEqual(p.dof, 5)
        self.assertEqual(p.id, 'open_manipulator_omx_f')


if __name__ == '__main__':
    unittest.main()
