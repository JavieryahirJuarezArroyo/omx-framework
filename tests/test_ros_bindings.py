"""Tests de inferencia de bindings (sin rclpy)."""
import os
import unittest

from agent.context import reload
from agent.ros_bindings import resolve_bindings
from agent.ros_schema import AgentRosSchema


class RosBindingsTests(unittest.TestCase):
    def tearDown(self):
        os.environ['ROS_AGENT_ROBOT'] = 'open_manipulator_omx_f'
        reload()

    def _load(self, robot_id: str):
        os.environ['ROS_AGENT_ROBOT'] = robot_id
        reload()
        from agent.context import get_profile

        return get_profile()

    def test_turtlesim_infer_cmd_vel_and_reset(self):
        p = self._load('turtlesim')
        b = p.ros_schema.bindings_for(p)
        self.assertEqual(b.state_topic, '/turtle1/pose')
        self.assertEqual(b.cmd_vel_topic, '/turtle1/cmd_vel')
        self.assertEqual(b.reset_service, '/reset')
        self.assertIsNone(b.trajectory)

    def test_arm_infer_trajectory(self):
        p = self._load('open_manipulator_omx_f')
        b = p.ros_schema.bindings_for(p)
        self.assertEqual(b.state_topic, '/joint_states')
        self.assertIsNotNone(b.trajectory)
        assert b.trajectory is not None
        self.assertIn('follow_joint_trajectory', b.trajectory.name)
        self.assertIsNotNone(b.gripper)
        self.assertIsNotNone(b.torque_service)

    def test_explicit_overrides_inferred(self):
        schema = AgentRosSchema.from_agent_ros(
            {
                'interfaces': [
                    {
                        'kind': 'topic_sub',
                        'name': '/joint_states',
                        'msg_type': 'sensor_msgs/msg/JointState',
                    }
                ],
                'motion': {'kind': 'joint_positions'},
                'bindings': {
                    'trajectory': {'name': '/custom/follow_joint_trajectory'}
                },
            }
        )
        p = self._load('generic_arm')
        b = resolve_bindings(schema, p, schema.bindings_raw)
        assert b.trajectory is not None
        self.assertEqual(b.trajectory.name, '/custom/follow_joint_trajectory')


if __name__ == '__main__':
    unittest.main()
