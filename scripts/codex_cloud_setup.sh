#!/usr/bin/env bash
# Codex Cloud setup helper for the project's target platform.
# Run only in an Ubuntu 22.04 environment. It does not access robot hardware.
set -euo pipefail

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
else
  echo "Cannot identify the operating system." >&2
  exit 1
fi

if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "22.04" ]]; then
  echo "This setup targets Ubuntu 22.04 LTS (ROS 2 Humble)." >&2
  echo "Detected: ${PRETTY_NAME:-unknown}. Use the ROS 2 Humble CI container instead." >&2
  exit 2
fi

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

$SUDO apt-get update
$SUDO apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release software-properties-common

$SUDO add-apt-repository -y universe

$SUDO curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" \
  | $SUDO tee /etc/apt/sources.list.d/ros2.list >/dev/null

$SUDO apt-get update
$SUDO apt-get install -y --no-install-recommends \
  ros-humble-ros-base \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-pip

if ! [[ -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  $SUDO rosdep init
fi
rosdep update

echo
echo "ROS 2 Humble setup complete."
echo "Before using ROS commands in a shell, run: source /opt/ros/humble/setup.bash"
