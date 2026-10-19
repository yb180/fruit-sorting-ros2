from pathlib import Path
import time
import unittest

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
import launch_testing
import launch_testing.actions
import launch_testing.asserts
from launch_ros.actions import Node
import pytest
import rclpy
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from fruit_sorting_interfaces.msg import (
    DetectionArray, ProduceDetection, SortingResult, SortingTarget,
)
from fruit_sorting_interfaces.srv import CommandHand, MoveArm


@pytest.mark.launch_test
def generate_test_description():
    demo = str(Path(get_package_share_directory('fruit_sorting_bringup')) /
               'launch' / 'demo.launch.py')
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(demo),
                                 launch_arguments={'namespace': 'healthy'}.items()),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(demo), launch_arguments={
            'namespace': 'failure', 'arm_fail_phase': 'place'}.items()),
        Node(package='fruit_sorting_planning', executable='sorting_planner',
             namespace='probe', parameters=[{'service_timeout': 0.5}], output='screen'),
        Node(package='fruit_sorting_planning', executable='sorting_planner',
             namespace='offline', parameters=[{'service_timeout': 0.5}], output='screen'),
        launch_testing.actions.ReadyToTest(),
    ])


class TestPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rclpy.init()
        cls.node = rclpy.create_node('pipeline_test_client')

    @classmethod
    def tearDownClass(cls):
        cls.node.destroy_node()
        rclpy.shutdown()

    def wait_for(self, condition, timeout=30.0):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.assertTrue(condition(), 'timed out waiting for expected ROS behavior')

    def test_pipeline_and_failure_boundaries(self):
        results = {name: [] for name in ('healthy', 'failure', 'probe', 'offline')}
        targets = []
        history = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        subscriptions = [self.node.create_subscription(
            SortingResult, f'/{name}/sorting/results',
            lambda msg, name=name: results[name].append(msg), history) for name in results]
        subscriptions.append(self.node.create_subscription(
            SortingTarget, '/healthy/sorting/targets', targets.append, history))
        self.wait_for(lambda: len(results['healthy']) >= 3 and len(results['failure']) >= 3)
        self.wait_for(lambda: len(targets) >= 3)
        self.assertEqual({target.class_label for target in targets},
                         {'apple', 'tomato', 'cucumber'})
        self.assertEqual(len({target.target_id for target in targets}), 3)
        bin_y = {'apple': -0.2, 'tomato': 0.0, 'cucumber': 0.2}
        for target in targets:
            self.assertEqual(target.pick_pose.header.frame_id, 'mock_table')
            self.assertEqual(target.place_pose.header.frame_id, 'mock_table')
            self.assertAlmostEqual(target.place_pose.pose.position.x, 0.4)
            self.assertAlmostEqual(target.place_pose.pose.position.y, bin_y[target.class_label])
            self.assertAlmostEqual(target.place_pose.pose.position.z, 0.05)
        for result in results['healthy']:
            self.assertTrue(result.success and result.simulated)
            self.assertEqual(result.stage, 'completed')
        for result in results['failure']:
            self.assertFalse(result.success)
            self.assertTrue(result.simulated)
            self.assertEqual(result.stage, 'arm_place')

        # Invalid requests must be rejected by the actual C++ mock servers.
        arm = self.node.create_client(MoveArm, '/healthy/arm/move')
        hand = self.node.create_client(CommandHand, '/healthy/hand/command')
        self.wait_for(lambda: arm.service_is_ready() and hand.service_is_ready())
        for client, request in [(arm, MoveArm.Request()), (hand, CommandHand.Request())]:
            future = client.call_async(request)
            self.wait_for(future.done)
            self.assertFalse(future.result().success)
            self.assertTrue(future.result().simulated)

        # Instrumented test services verify the planner's order and stop behavior.
        calls = []

        def on_arm(request, response):
            calls.append((request.target_id, 'arm', request.phase))
            if request.target_id == 'sort-probe-timeout':
                time.sleep(1.2)
            response.success = True
            response.simulated = request.target_id != 'sort-probe-real'
            response.message = 'test service'
            return response

        def on_hand(request, response):
            calls.append((request.target_id, 'hand', request.command))
            response.success = request.target_id != 'sort-probe-failure'
            response.simulated = True
            response.message = 'injected hand failure'
            return response

        arm_server = self.node.create_service(MoveArm, '/probe/arm/move', on_arm)
        hand_server = self.node.create_service(CommandHand, '/probe/hand/command', on_hand)
        publishers = {name: self.node.create_publisher(
            DetectionArray, f'/{name}/perception/detections', 10)
            for name in ('probe', 'offline')}
        self.wait_for(lambda: all(pub.get_subscription_count() for pub in publishers.values()))

        def publish(name, detection_id):
            detection = ProduceDetection()
            detection.detection_id = detection_id
            detection.class_label = 'apple'
            detection.confidence = 0.95
            detection.pose.header.frame_id = 'mock_table'
            detection.pose.pose.orientation.w = 1.0
            message = DetectionArray()
            message.detections = [detection]
            publishers[name].publish(message)

        publish('probe', 'probe-success')
        self.wait_for(lambda: len(results['probe']) == 1)
        self.assertTrue(results['probe'][0].success)
        expected = [('arm', 'pick'), ('hand', 'close'), ('arm', 'place'), ('hand', 'open')]
        self.assertEqual([(device, action) for _, device, action in calls], expected)
        # Repeated detections must not trigger a second sequence.
        publish('probe', 'probe-success')
        publish('probe', 'probe-failure')
        self.wait_for(lambda: len(results['probe']) == 2)
        self.assertFalse(results['probe'][1].success)
        self.assertEqual(results['probe'][1].stage, 'hand_close')
        self.assertEqual([(device, action) for target, device, action in calls
                          if target == 'sort-probe-failure'], expected[:2])
        publish('probe', 'probe-real')
        self.wait_for(lambda: len(results['probe']) == 3)
        self.assertFalse(results['probe'][2].success)
        self.assertIn('non-simulated', results['probe'][2].message)
        publish('probe', 'probe-timeout')
        self.wait_for(lambda: len(results['probe']) == 4)
        self.assertFalse(results['probe'][3].success)
        self.assertIn('response timeout', results['probe'][3].message)
        publish('offline', 'offline-001')
        self.wait_for(lambda: len(results['offline']) == 1)
        self.assertFalse(results['offline'][0].success)
        self.assertIn('unavailable', results['offline'][0].message)
        # Allow more perception frames and the late timeout response to arrive.
        end = time.monotonic() + 1.2
        while time.monotonic() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)
        self.assertEqual(len(results['healthy']), 3)
        self.assertEqual(len(results['failure']), 3)
        self.assertEqual(len(results['probe']), 4)
        for target in ('sort-probe-real', 'sort-probe-timeout'):
            self.assertEqual([(device, action) for tid, device, action in calls if tid == target],
                             [('arm', 'pick')])
        self.node.destroy_service(arm_server)
        self.node.destroy_service(hand_server)


@launch_testing.post_shutdown_test()
class TestShutdown(unittest.TestCase):
    def test_processes_exit_cleanly(self, proc_info):
        launch_testing.asserts.assertExitCodes(proc_info)
