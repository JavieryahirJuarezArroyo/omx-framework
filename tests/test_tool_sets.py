"""Tools generadas dinámicamente desde agent.ros."""
import os
import unittest

from agent.context import reload
from agent.tool_codegen import generate_tool_specs
from agent.ros_schema import AgentRosSchema
from agent.context import get_profile
from agent.tools_lc import get_agent_tools, reset_tools_cache


class ToolSetTests(unittest.TestCase):
    def tearDown(self):
        os.environ['ROS_AGENT_ROBOT'] = 'open_manipulator_omx_f'
        reload()
        reset_tools_cache()

    def test_arm_tools_from_ros_schema(self):
        os.environ['ROS_AGENT_ROBOT'] = 'open_manipulator_omx_f'
        reload()
        reset_tools_cache()
        names = {t.name for t in get_agent_tools()}
        self.assertIn('move_to_joints', names)
        self.assertIn('get_robot_state', names)
        self.assertNotIn('drive', names)

    def test_mobile_tools_from_ros_schema(self):
        os.environ['ROS_AGENT_ROBOT'] = 'turtlesim'
        reload()
        reset_tools_cache()
        names = {t.name for t in get_agent_tools()}
        self.assertIn('drive', names)
        self.assertIn('get_pose', names)
        self.assertNotIn('move_to_joints', names)

    def test_codegen_joint_motion(self):
        os.environ['ROS_AGENT_ROBOT'] = 'open_manipulator_omx_f'
        reload()
        p = get_profile()
        specs = generate_tool_specs(p, p.ros_schema)
        motion = [s for s in specs if s.name == 'move_to_joints'][0]
        self.assertEqual(motion.bridge.op, 'move_joints')
        self.assertTrue(motion.bridge.safety_max_step)


if __name__ == '__main__':
    unittest.main()
