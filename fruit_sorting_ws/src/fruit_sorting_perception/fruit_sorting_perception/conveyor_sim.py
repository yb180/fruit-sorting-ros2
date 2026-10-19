"""Moving synthetic objects and a logical stop/start service; no hardware IO."""
from copy import deepcopy
from math import isfinite
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile

from fruit_sorting_interfaces.msg import (
    ConveyorState, DetectionArray, ProduceDetection, SortingResult,
)
from fruit_sorting_interfaces.srv import SetConveyor


class ConveyorSimulator(Node):
    def __init__(self):
        super().__init__('conveyor_simulator')
        self.declare_parameter('speed', 0.1)
        self.declare_parameter('spacing', 0.2)
        self.declare_parameter('fail_stop', False)
        self.declare_parameter('fail_start', False)
        self.speed = float(self.get_parameter('speed').value)
        spacing = float(self.get_parameter('spacing').value)
        if not all(isfinite(v) and v > 0 for v in (self.speed, spacing)):
            raise ValueError('simulation speed and spacing must be positive and finite')
        self.running = True
        self.offset = 0.0
        self.last_update = time.monotonic()
        self.items = {}
        for i, label in enumerate(('apple', 'banana', 'pear', 'tomato')):
            item = ProduceDetection()
            item.detection_id = f'belt-{label}-001'
            item.class_label = label
            item.confidence = 0.95
            item.pose.header.frame_id = 'mock_table'
            item.pose.pose.position.x = -0.1 - i * spacing
            item.pose.pose.position.z = 0.05
            item.pose.pose.orientation.w = 1.0
            self.items[item.detection_id] = item
        self.detections = self.create_publisher(DetectionArray, 'perception/detections', 10)
        history = QoSProfile(depth=10, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.states = self.create_publisher(ConveyorState, 'conveyor/state', history)
        self.service = self.create_service(SetConveyor, 'conveyor/set_running', self.command)
        self.results = self.create_subscription(
            SortingResult, 'sorting/results', self.on_sort_result, 10)
        self.timer = self.create_timer(0.05, self.publish_scene)

    def advance(self):
        now = time.monotonic()
        if self.running:
            self.offset += self.speed * (now - self.last_update)
        self.last_update = now

    def command(self, request, response):
        self.advance()
        fail = self.get_parameter('fail_start' if request.running else 'fail_stop').value
        response.success = not fail
        response.simulated = True
        if not fail:
            self.running = request.running
        response.running = self.running
        response.message = 'injected conveyor failure' if fail else 'simulated conveyor updated'
        return response

    def on_sort_result(self, message):
        if not (message.success and message.simulated):
            return
        for detection_id in list(self.items):
            if message.target_id == f'sort-{detection_id}':
                del self.items[detection_id]

    def publish_scene(self):
        self.advance()
        stamp = self.get_clock().now().to_msg()
        state = ConveyorState()
        state.header.stamp = stamp
        state.header.frame_id = 'mock_table'
        state.running = self.running
        state.simulated = True
        self.states.publish(state)
        message = DetectionArray()
        message.header = state.header
        for item in self.items.values():
            current = deepcopy(item)
            current.pose.header.stamp = stamp
            current.pose.pose.position.x += self.offset
            # Synthetic camera field of view; no out-of-view target is grasped.
            if -0.2 <= current.pose.pose.position.x <= 0.5:
                message.detections.append(current)
        self.detections.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = ConveyorSimulator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
