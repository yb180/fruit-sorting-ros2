cmake_minimum_required(VERSION 3.8)
project(fruit_sorting_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ProduceDetection.msg"
  "msg/DetectionArray.msg"
  "msg/SortingTarget.msg"
  "msg/SortingResult.msg"
  "srv/MoveArm.srv"
  "srv/CommandHand.srv"
  DEPENDENCIES std_msgs geometry_msgs)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
