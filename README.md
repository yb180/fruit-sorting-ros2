# Fruit Sorting ROS 2

Starter repository for a conveyor-belt fruit/vegetable sorting system using ROS 2 Humble.

## Target platform
- Ubuntu 22.04 LTS
- ROS 2 Humble
- Python 3

## Current scope
This is a safe software-only starter. It publishes a sample detected-item message as a log/output placeholder; it does not control real hardware.

## Build on Ubuntu 22.04 with ROS 2 Humble
```bash
source /opt/ros/humble/setup.bash
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-rosdep
sudo rosdep init  # run once per machine; skip if already initialized
rosdep update
cd fruit-sorting-ros2
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 run fruit_sorting_bringup sorting_demo
```

## Next milestones
1. Add camera/vision pipeline and define a stable detection message interface.
2. Add robot-specific motion planning integration (for example, MoveIt 2) after the robot model is known.
3. Add gripper/hand interface only after the hardware and driver APIs are confirmed.
4. Validate in simulation before any real robot motion.

## Cloud development
Codex Cloud environment creation and publishing must be completed in the Codex UI. The GitHub Actions workflow in this repository provides a separate ROS 2 Humble build check.
