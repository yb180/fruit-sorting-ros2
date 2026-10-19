import rclpy
from rclpy.node import Node

from fruit_sorting_interfaces.msg import DetectionArray, ProduceDetection
from fruit_sorting_perception.fixtures import DETECTIONS


class MockPerception(Node):
    def __init__(self):
        super().__init__('perception_mock')
        self.declare_parameter('publish_period', 1.0)
        period = float(self.get_parameter('publish_period').value)
        if not 0.05 <= period <= 60.0:
            raise ValueError('publish_period must be between 0.05 and 60 seconds')
        self.publisher = self.create_publisher(DetectionArray, 'perception/detections', 10)
        self.timer = self.create_timer(period, self.publish_detections)
        self.get_logger().info('Publishing synthetic detections; no camera is connected')

    def publish_detections(self):
        message = DetectionArray()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = 'mock_table'
        for detection_id, label, confidence, x, y, z in DETECTIONS:
            detection = ProduceDetection()
            detection.detection_id = detection_id
            detection.class_label = label
            detection.confidence = confidence
            detection.pose.header = message.header
            detection.pose.pose.position.x = x
            detection.pose.pose.position.y = y
            detection.pose.pose.position.z = z
            detection.pose.pose.orientation.w = 1.0
            message.detections.append(detection)
        self.publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = MockPerception()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
