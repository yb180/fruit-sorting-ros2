#!/usr/bin/env bash
set -eo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/ros/humble/setup.bash
cd "$repo_root/fruit_sorting_ws"
colcon build --symlink-install --executor sequential --event-handlers console_direct+ \
  --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo
source install/setup.bash
colcon test --executor sequential --event-handlers console_direct+ --return-code-on-test-failure
colcon test-result --verbose
