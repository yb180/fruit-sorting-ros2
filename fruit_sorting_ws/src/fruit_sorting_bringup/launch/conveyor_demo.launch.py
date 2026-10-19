"""Logical moving-belt demo with no physical controllers, camera or CAN."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    config = Path(get_package_share_directory('fruit_sorting_bringup')) / 'config'
    namespace = LaunchConfiguration('namespace')
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('hand_fail_command', default_value=''),
        DeclareLaunchArgument('fail_stop', default_value='false'),
        DeclareLaunchArgument('fail_start', default_value='false'),
        Node(package='fruit_sorting_perception', executable='conveyor_simulator',
             namespace=namespace, output='screen', parameters=[{
                 'fail_stop': ParameterValue(LaunchConfiguration('fail_stop'), value_type=bool),
                 'fail_start': ParameterValue(LaunchConfiguration('fail_start'), value_type=bool),
             }]),
        Node(package='fruit_sorting_planning', executable='conveyor_coordinator',
             namespace=namespace, output='screen', parameters=[str(config / 'conveyor.yaml')]),
        Node(package='fruit_sorting_planning', executable='sorting_planner',
             namespace=namespace, output='screen',
             parameters=[str(config / 'planning_conveyor.yaml')],
             # Conveyor goals enter through an acknowledged service, never this topic.
             remappings=[('perception/detections', 'sorting/unused_detections')]),
        Node(package='fruit_sorting_planning', executable='mock_arm',
             namespace=namespace, output='screen'),
        Node(package='fruit_sorting_planning', executable='mock_hand',
             namespace=namespace, output='screen',
             parameters=[{'fail_command': LaunchConfiguration('hand_fail_command')}]),
    ])
