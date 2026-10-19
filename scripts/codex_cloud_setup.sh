#!/usr/bin/env bash
# Codex Cloud setup helper for the fruit-sorting project.
# Installs general tools everywhere; installs native ROS 2 Humble only on Ubuntu 22.04.
set -euo pipefail

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
else
  echo "Cannot identify the operating system; installing basic tools only." >&2
  ID="unknown"
  VERSION_ID="unknown"
fi

if [[ "$(id -u)" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

$SUDO apt-get update
$SUDO apt-get install -y --no-install-recommends \
  ca-certificates curl git gnupg lsb-release build-essential cmake \
  python3 python3-pip python3-venv

if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "22.04" ]]; then
  echo
  echo "Detected ${PRETTY_NAME:-unknown}; installed general development tools only."
  echo "Native ROS 2 Humble packages target Ubuntu 22.04. Use the repository's"
  echo "GitHub Actions workflow (ros:humble-ros-base) to build/test ROS packages."
  exit 0
fi

$SUDO apt-get install -y --no-install-recommends \
  software-properties-common
$SUDO add-apt-repository -y universe

$SUDO curl -fsSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu jammy main" \
  | $SUDO tee /etc/apt/sources.list.d/ros2.list >/dev/null

$SUDO apt-get update
$SUDO apt-get install -y --no-install-recommends \
  ros-humble-ros-base \
  python3-colcon-common-extensions \
  python3-rosdep

if ! [[ -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  $SUDO rosdep init
fi
rosdep update

echo
echo "ROS 2 Humble setup complete."
echo "Before using ROS commands in a shell, run: source /opt/ros/humble/setup.bash"
