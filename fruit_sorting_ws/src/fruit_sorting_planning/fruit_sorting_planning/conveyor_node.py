"""Simulation-only stop-and-pick coordinator around the existing mock planner."""
from copy import deepcopy
from math import isfinite
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile

from fruit_sorting_interfaces.msg import ConveyorState, DetectionArray, SortingResult
from fruit_sorting_interfaces.srv import SetConveyor, SubmitDetection
from fruit_sorting_planning.conveyor_policy import fresh_sample, in_pick_window
from fruit_sorting_planning.policy import Candidate, response_error, select_bin


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


class ConveyorCoordinator(Node):
    def __init__(self):
        super().__init__('conveyor_coordinator')
        parameters = {
            'pick_x_min': 0.1, 'pick_x_max': 0.3, 'sample_max_age': 0.5,
            'service_timeout': 5.0, 'sorting_timeout': 30.0,
            'minimum_confidence': 0.8, 'max_targets': 100,
            'labels': ['apple', 'banana', 'pear', 'tomato'],
        }
        for name, value in parameters.items():
            self.declare_parameter(name, value)
        self.x_min = float(self.get_parameter('pick_x_min').value)
        self.x_max = float(self.get_parameter('pick_x_max').value)
        self.max_age = float(self.get_parameter('sample_max_age').value)
        self.timeout = float(self.get_parameter('service_timeout').value)
        self.sorting_timeout = float(self.get_parameter('sorting_timeout').value)
        self.minimum_confidence = float(self.get_parameter('minimum_confidence').value)
        self.max_targets = int(self.get_parameter('max_targets').value)
        self.labels = set(self.get_parameter('labels').value)
        in_pick_window(self.x_min, self.x_min, self.x_max)
        if (not all(isfinite(v) and v > 0 for v in (
                self.max_age, self.timeout, self.sorting_timeout))
                or not self.labels or self.max_targets <= 0
                or not isfinite(self.minimum_confidence)
                or not 0 <= self.minimum_confidence <= 1):
            raise ValueError('invalid conveyor coordinator configuration')
        self.phase = 'seek'
        self.active_id = None
        self.seen = set()
        self.latest = DetectionArray()
        self.belt_state = None
        self.future = None
        self.early_result = None
        self.deadline = None
        self.ack_ns = 0
        self.belt = self.create_client(SetConveyor, 'conveyor/set_running')
        self.sorter = self.create_client(SubmitDetection, 'sorting/submit_detection')
        history = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.cycles = self.create_publisher(SortingResult, 'conveyor/cycle_results', history)
        self.approved = self.create_publisher(DetectionArray, 'sorting/approved_detections', 10)
        self.detections = self.create_subscription(
            DetectionArray, 'perception/detections', self.on_detections, 10)
        self.states = self.create_subscription(
            ConveyorState, 'conveyor/state', self.on_state, history)
        self.results = self.create_subscription(
            SortingResult, 'sorting/results', self.on_result, history)
        self.timer = self.create_timer(0.05, self.tick)
        self.get_logger().info('Simulation conveyor coordinator: seek → stop → sort → resume')

    def on_detections(self, message):
        self.latest = message

    def on_state(self, message):
        self.belt_state = message

    def eligible(self, detection, after_ns=None):
        now_ns = self.get_clock().now().nanoseconds
        if not fresh_sample(stamp_ns(detection.pose.header.stamp), now_ns,
                            self.max_age, after_ns):
            return False
        p = detection.pose.pose.position
        q = detection.pose.pose.orientation
        candidate = Candidate(detection.detection_id, detection.class_label,
                              detection.confidence, detection.pose.header.frame_id,
                              (p.x, p.y, p.z), (q.x, q.y, q.z, q.w))
        # Only category membership is used here; the sorter assigns destination bins.
        try:
            accepted = select_bin(candidate, {label: True for label in self.labels},
                                  self.minimum_confidence, 'mock_table')
            return accepted is not None and in_pick_window(p.x, self.x_min, self.x_max)
        except ValueError:
            return False

    def state_matches(self, running, after_ns=None):
        state = self.belt_state
        return (state is not None and state.simulated and state.running == running
                and state.header.frame_id == 'mock_table'
                and fresh_sample(stamp_ns(state.header.stamp),
                                 self.get_clock().now().nanoseconds,
                                 self.max_age, after_ns))

    def begin_command(self, running):
        self.phase = 'starting' if running else 'stopping'
        self.deadline = time.monotonic() + self.timeout
        self.future = None

    def finish(self, success, reason):
        result = SortingResult()
        result.header.stamp = self.get_clock().now().to_msg()
        result.header.frame_id = 'mock_table'
        result.target_id = f'sort-{self.active_id}'
        result.success = success
        result.simulated = True
        result.stage = 'completed' if success else self.phase
        result.message = reason
        self.cycles.publish(result)
        self.get_logger().info(f'{result.target_id}: {result.stage}: {reason}')
        if self.future is not None and not self.future.done():
            self.future.cancel()
        self.future = None
        self.phase = 'seek' if success else 'halted'
        self.active_id = None

    def on_result(self, result):
        if result.target_id != f'sort-{self.active_id}':
            return
        if self.phase == 'submitting':
            self.early_result = result
            return
        if self.phase != 'sorting':
            return
        error = response_error(result)
        if error:
            self.finish(False, f'sorting failed at {result.stage}: {error}; belt not resumed')
        else:
            self.begin_command(True)

    def tick(self):
        if self.phase == 'halted':
            return
        if self.phase == 'seek':
            if len(self.seen) >= self.max_targets or not self.state_matches(True):
                return
            candidates = [d for d in self.latest.detections
                          if d.detection_id not in self.seen and self.eligible(d)]
            if not candidates:
                return
            candidate = max(candidates, key=lambda d: d.pose.pose.position.x)
            self.active_id = candidate.detection_id
            self.seen.add(self.active_id)
            self.begin_command(False)
        if time.monotonic() >= self.deadline:
            self.finish(False, f'{self.phase} timeout; coordinator halted')
            return
        if self.phase == 'submitting':
            if not self.future.done():
                return
            try:
                error = response_error(self.future.result())
            except Exception as exception:
                error = f'sorter admission exception: {exception}'
            if error:
                self.finish(False, error)
                return
            self.future = None
            self.phase = 'sorting'
            self.deadline = time.monotonic() + self.sorting_timeout
            if self.early_result is not None:
                result = self.early_result
                self.early_result = None
                self.on_result(result)
            return
        if self.phase in ('stopping', 'starting'):
            desired = self.phase == 'starting'
            if self.future is None:
                if self.belt.service_is_ready():
                    request = SetConveyor.Request()
                    request.running = desired
                    try:
                        self.future = self.belt.call_async(request)
                    except Exception as error:
                        self.finish(False, f'conveyor request exception: {error}')
                return
            if not self.future.done():
                return
            try:
                response = self.future.result()
                error = response_error(response)
                if not error and response.running != desired:
                    error = 'conveyor acknowledgement state mismatch'
            except Exception as exception:
                error = f'conveyor service exception: {exception}'
            if error:
                self.finish(False, error)
                return
            self.future = None
            self.ack_ns = self.get_clock().now().nanoseconds
            self.deadline = time.monotonic() + self.timeout
            self.phase = 'confirm_start' if desired else 'confirm_stop'
            return
        if self.phase == 'confirm_stop':
            if not self.state_matches(False, self.ack_ns):
                return
            detection = next((d for d in self.latest.detections
                              if d.detection_id == self.active_id
                              and self.eligible(d, self.ack_ns)), None)
            if detection is None or not self.sorter.service_is_ready():
                return
            message = DetectionArray()
            message.header = deepcopy(self.latest.header)
            message.detections = [deepcopy(detection)]
            request = SubmitDetection.Request()
            request.detection = deepcopy(detection)
            self.phase = 'submitting'
            self.early_result = None
            self.deadline = time.monotonic() + self.timeout
            try:
                self.future = self.sorter.call_async(request)
            except Exception as exception:
                self.finish(False, f'sorter admission request exception: {exception}')
                return
            self.approved.publish(message)
        elif self.phase == 'confirm_start' and self.state_matches(True, self.ack_ns):
            self.finish(True, 'simulated conveyor stopped, target sorted and conveyor resumed')


def main(args=None):
    rclpy.init(args=args)
    node = ConveyorCoordinator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
