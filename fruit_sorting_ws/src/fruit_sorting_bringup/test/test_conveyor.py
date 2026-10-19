from pathlib import Path
import time
import unittest

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import launch_testing
import launch_testing.actions
import launch_testing.asserts
import pytest
import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile

from fruit_sorting_interfaces.msg import ConveyorState, DetectionArray, SortingResult


@pytest.mark.launch_test
def generate_test_description():
    path = str(Path(get_package_share_directory('fruit_sorting_bringup')) /
               'launch' / 'conveyor_demo.launch.py')
    actions = []
    for namespace, extra in [
        ('belt_ok', {}), ('belt_hand_fault', {'hand_fail_command': 'close'}),
        ('belt_stop_fault', {'fail_stop': 'true'}),
        ('belt_resume_fault', {'fail_start': 'true'}),
    ]:
        actions.append(GroupAction([
            IncludeLaunchDescription(PythonLaunchDescriptionSource(path),
                                     launch_arguments={'namespace': namespace, **extra}.items())
        ]))
    return LaunchDescription(actions + [launch_testing.actions.ReadyToTest()])


def ns_stamp(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


class TestConveyor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('conveyor_test_client')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def test_moving_arrivals_stopped_pick_resume_and_fault_latching(self):
        namespaces = ['belt_ok', 'belt_hand_fault', 'belt_stop_fault', 'belt_resume_fault']
        cycles = {key: [] for key in namespaces}
        approved = {key: [] for key in namespaces}
        states = {key: [] for key in namespaces}
        positions = {}
        history = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        subscriptions = []
        for name in namespaces:
            for message_type, topic, output, qos in [
                (SortingResult, 'conveyor/cycle_results', cycles[name], history),
                (ConveyorState, 'conveyor/state', states[name], history),
                (DetectionArray, 'sorting/approved_detections', approved[name], 10),
            ]:
                subscriptions.append(self.node.create_subscription(
                    message_type, f'/{name}/{topic}', output.append, qos))

        def record_positions(message):
            for detection in message.detections:
                positions.setdefault(detection.detection_id, set()).add(
                    round(detection.pose.pose.position.x, 4))

        subscriptions.append(self.node.create_subscription(
            DetectionArray, '/belt_ok/perception/detections', record_positions, 10))
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if len(cycles['belt_ok']) == 4 and all(cycles[key] for key in namespaces[1:]):
                break
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.assertEqual(len(cycles['belt_ok']), 4)
        self.assertEqual(len(approved['belt_ok']), 4)
        self.assertEqual({msg.detections[0].class_label for msg in approved['belt_ok']},
                         {'apple', 'banana', 'pear', 'tomato'})
        self.assertEqual(len({result.target_id for result in cycles['belt_ok']}), 4)
        for result in cycles['belt_ok']:
            self.assertTrue(result.success and result.simulated)
            self.assertEqual(result.stage, 'completed')
        self.assertTrue(any(len(samples) >= 3 for samples in positions.values()))
        for message in approved['belt_ok']:
            self.assertEqual(len(message.detections), 1)
            detection = message.detections[0]
            self.assertGreaterEqual(detection.pose.pose.position.x, 0.1)
            self.assertLessEqual(detection.pose.pose.position.x, 0.3)
            # The authorized scene must correspond to feedback with the belt stopped.
            self.assertTrue(any(not state.running and state.simulated
                                and ns_stamp(state.header.stamp) == ns_stamp(message.header.stamp)
                                for state in states['belt_ok']))
        self.assertTrue(states['belt_ok'][-1].running)

        expected = {'belt_hand_fault': 'sorting', 'belt_stop_fault': 'stopping',
                    'belt_resume_fault': 'starting'}
        for name, stage in expected.items():
            self.assertEqual(len(cycles[name]), 1)
            self.assertFalse(cycles[name][0].success)
            self.assertTrue(cycles[name][0].simulated)
            self.assertEqual(cycles[name][0].stage, stage)
        self.assertEqual(len(approved['belt_stop_fault']), 0)
        self.assertEqual(len(approved['belt_hand_fault']), 1)
        self.assertEqual(len(approved['belt_resume_fault']), 1)
        self.assertFalse(states['belt_hand_fault'][-1].running)
        self.assertFalse(states['belt_resume_fault'][-1].running)
        # Faults latch: no automatic retry, second target or resume after hand failure.
        end = time.monotonic() + 0.8
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.assertEqual(len(cycles['belt_ok']), 4)
        for name in expected:
            self.assertEqual(len(cycles[name]), 1)
        self.assertEqual(len(approved['belt_hand_fault']), 1)


@launch_testing.post_shutdown_test()
class TestConveyorShutdown(unittest.TestCase):
    def test_processes_exit_cleanly(self, proc_info):
        launch_testing.asserts.assertExitCodes(proc_info)
