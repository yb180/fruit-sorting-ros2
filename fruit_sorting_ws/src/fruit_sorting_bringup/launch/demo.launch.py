from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    config = Path(get_package_share_directory('fruit_sorting_bringup')) / 'config'
    namespace = LaunchConfiguration('namespace')
    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('arm_fail_phase', default_value=''),
        DeclareLaunchArgument('hand_fail_command', default_value=''),
        Node(package='fruit_sorting_perception', executable='mock_perception',
             name='perception_mock', namespace=namespace, output='screen',
             parameters=[str(config / 'perception.yaml')]),
        Node(package='fruit_sorting_planning', executable='sorting_planner',
             name='sorting_planner', namespace=namespace, output='screen',
             parameters=[str(config / 'planning.yaml')]),
        Node(package='fruit_sorting_planning', executable='mock_arm',
             name='mock_arm', namespace=namespace, output='screen',
             parameters=[{'fail_phase': LaunchConfiguration('arm_fail_phase')}]),
        Node(package='fruit_sorting_planning', executable='mock_hand',
             name='mock_hand', namespace=namespace, output='screen',
             parameters=[{'fail_command': LaunchConfiguration('hand_fail_command')}]),
    ])
