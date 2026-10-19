#!/usr/bin/env bash
set -eo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != 22.04 ]]; then
  echo 'Run this script on Ubuntu 22.04 (native or inside the Humble container).' >&2
  exit 1
fi
if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  echo 'Install ROS 2 Humble first using the official instructions, or use the ROS image.' >&2
  exit 1
fi
source /opt/ros/humble/setup.bash
elevate=()
if [[ "$EUID" != 0 ]]; then elevate=(sudo); fi
if ! command -v rosdep >/dev/null || ! command -v colcon >/dev/null; then
  "${elevate[@]}" apt-get update
  "${elevate[@]}" apt-get install -y --no-install-recommends python3-rosdep python3-colcon-common-extensions
fi
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  "${elevate[@]}" rosdep init
fi
rosdep update --rosdistro humble
if ! rosdep check --from-paths "$repo_root/fruit_sorting_ws/src" --ignore-src --rosdistro humble; then
  # Refresh apt metadata only if a declared dependency needs installation.
  "${elevate[@]}" apt-get update
fi
rosdep install --from-paths "$repo_root/fruit_sorting_ws/src" \
  --ignore-src --rosdistro humble -y
