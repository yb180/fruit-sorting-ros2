from collections import deque
from copy import deepcopy
from math import isfinite
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

from fruit_sorting_interfaces.msg import DetectionArray, SortingResult, SortingTarget
from fruit_sorting_interfaces.srv import CommandHand, MoveArm, SubmitDetection
from fruit_sorting_planning.policy import (
    Candidate, STEPS, make_bins, response_error, select_bin,
)


class SortingPlanner(Node):
    """Single-target, nonblocking state machine for mock controllers only."""

    def __init__(self):
        super().__init__('sorting_planner')
        defaults = {
            'minimum_confidence': 0.8,
            'frame_id': 'mock_table',
            'bin_labels': ['apple', 'tomato', 'cucumber'],
            'bin_positions': [0.4, -0.2, 0.05, 0.4, 0.0, 0.05, 0.4, 0.2, 0.05],
            'service_timeout': 5.0,
            'max_targets': 100,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value)
        self.minimum_confidence = self.get_parameter('minimum_confidence').value
        self.frame_id = self.get_parameter('frame_id').value
        self.bins = make_bins(self.get_parameter('bin_labels').value,
                              self.get_parameter('bin_positions').value)
        self.timeout = float(self.get_parameter('service_timeout').value)
        self.max_targets = int(self.get_parameter('max_targets').value)
        if (not isfinite(self.timeout) or self.timeout <= 0 or self.max_targets <= 0
                or not self.frame_id or not isfinite(self.minimum_confidence)
                or not 0 <= self.minimum_confidence <= 1):
            raise ValueError('invalid timeout, target limit, frame or confidence parameters')
        # Retain a bounded history so a late subscriber can inspect this demo run.
        history = QoSProfile(depth=self.max_targets,
                             reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.target_pub = self.create_publisher(SortingTarget, 'sorting/targets', history)
        self.result_pub = self.create_publisher(SortingResult, 'sorting/results', history)
        self.subscription = self.create_subscription(
            DetectionArray, 'perception/detections', self.on_detections, 10)
        self.arm = self.create_client(MoveArm, 'arm/move')
        self.hand = self.create_client(CommandHand, 'hand/command')
        self.queue = deque()
        self.seen = set()
        self.admission = self.create_service(
            SubmitDetection, 'sorting/submit_detection', self.submit_detection)
        self.active = None
        self.future = None
        self.step = 0
        self.deadline = None
        self.timer = self.create_timer(0.05, self.tick)
        self.get_logger().info('Simulation-only sorting planner started')

    def submit_detection(self, request, response):
        detection_id = request.detection.detection_id
        response.simulated = True
        if detection_id in self.seen:
            response.success = False
            response.message = 'detection already admitted in this run'
            return response
        message = DetectionArray()
        message.detections = [request.detection]
        self.on_detections(message)
        response.success = detection_id in self.seen
        response.message = 'simulated target queued' if response.success else 'detection rejected'
        return response

    def on_detections(self, message):
        for detection in message.detections:
            if detection.detection_id in self.seen or len(self.seen) >= self.max_targets:
                continue
            pose = detection.pose.pose
            candidate = Candidate(
                detection.detection_id, detection.class_label, detection.confidence,
                detection.pose.header.frame_id,
                (pose.position.x, pose.position.y, pose.position.z),
                (pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w))
            try:
                destination = select_bin(candidate, self.bins,
                                         self.minimum_confidence, self.frame_id)
            except ValueError as error:
                self.get_logger().warning(f'Rejected detection: {error}')
                continue
            if destination is None:
                continue
            target = SortingTarget()
            target.target_id = f'sort-{candidate.detection_id}'
            target.detection_id = candidate.detection_id
            target.class_label = candidate.label
            target.pick_pose = deepcopy(detection.pose)
            target.place_pose = deepcopy(detection.pose)
            target.place_pose.pose.position.x = destination[0]
            target.place_pose.pose.position.y = destination[1]
            target.place_pose.pose.position.z = destination[2]
            self.seen.add(candidate.detection_id)
            self.queue.append(target)

    def stage(self):
        if self.step >= len(STEPS):
            return 'completed'
        device, command = STEPS[self.step]
        return f'{device}_{command}'

    def finish(self, success, message):
        result = SortingResult()
        result.header.stamp = self.get_clock().now().to_msg()
        result.header.frame_id = self.frame_id
        result.target_id = self.active.target_id
        result.success = success
        # This reports a simulation pipeline outcome, not proof of physical execution.
        result.simulated = True
        result.stage = self.stage()
        result.message = message
        self.result_pub.publish(result)
        self.get_logger().info(f'{result.target_id}: {result.stage}: {message}')
        self.active = None
        self.future = None
        self.deadline = None

    def tick(self):
        if self.active is None:
            if not self.queue:
                return
            self.active = self.queue.popleft()
            self.step = 0
            self.deadline = time.monotonic() + self.timeout
            self.target_pub.publish(self.active)
        if self.future is not None:
            if not self.future.done():
                if time.monotonic() >= self.deadline:
                    self.future.cancel()
                    self.finish(False, 'service response timeout; remaining steps cancelled')
                return
            try:
                error = response_error(self.future.result())
            except Exception as exception:  # Transport/service failures become explicit results.
                error = f'service exception: {exception}'
            if error:
                self.finish(False, error)
                return
            self.future = None
            self.step += 1
            if self.step == len(STEPS):
                self.finish(True, 'simulated pick and place completed')
                return
            self.deadline = time.monotonic() + self.timeout
        device, command = STEPS[self.step]
        client = self.arm if device == 'arm' else self.hand
        # Require both controllers before beginning a target.
        if not (self.arm.service_is_ready() and self.hand.service_is_ready()):
            if time.monotonic() >= self.deadline:
                self.finish(False, 'mock services unavailable; remaining steps cancelled')
            return
        if device == 'arm':
            request = MoveArm.Request()
            request.phase = command
            request.target_pose = (self.active.pick_pose if command == 'pick'
                                   else self.active.place_pose)
        else:
            request = CommandHand.Request()
            request.command = command
            request.class_label = self.active.class_label
        request.target_id = self.active.target_id
        try:
            self.future = client.call_async(request)
            self.deadline = time.monotonic() + self.timeout
        except Exception as exception:
            self.finish(False, f'could not send service request: {exception}')


def main(args=None):
    rclpy.init(args=args)
    node = SortingPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
