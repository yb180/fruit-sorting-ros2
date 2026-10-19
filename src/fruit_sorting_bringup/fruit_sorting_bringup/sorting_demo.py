"""Safe starter node for the fruit sorting project.

This node demonstrates a software-only workflow and does not command hardware.
"""
import rclpy
from rclpy.node import Node


class SortingDemo(Node):
    def __init__(self):
        super().__init__("sorting_demo")
        self.get_logger().info(
            "Fruit sorting starter is running. No robot hardware is connected."
        )
        self.get_logger().info(
            "Next step: replace this placeholder with camera detections and a "
            "robot-specific, safety-validated planning interface."
        )


def main(args=None):
    rclpy.init(args=args)
    node = SortingDemo()
    try:
        rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
