#include <cmath>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "fruit_sorting_interfaces/srv/move_arm.hpp"

class MockArm : public rclcpp::Node
{
public:
  MockArm() : Node("mock_arm")
  {
    fail_phase_ = declare_parameter<std::string>("fail_phase", "");
    service_ = create_service<Service>("arm/move",
      [this](const std::shared_ptr<Service::Request> request,
      std::shared_ptr<Service::Response> response) {
        const auto & pose = request->target_pose.pose;
        const auto & q = pose.orientation;
        const double norm = std::sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w);
        const bool valid = !request->target_id.empty() &&
          request->target_pose.header.frame_id == "mock_table" &&
          (request->phase == "pick" || request->phase == "place") &&
          std::isfinite(pose.position.x) && std::isfinite(pose.position.y) &&
          std::isfinite(pose.position.z) && std::isfinite(norm) &&
          std::abs(norm - 1.0) <= 1e-3;
        response->simulated = true;
        response->success = valid && request->phase != fail_phase_;
        response->message = !valid ? "invalid mock arm request" :
          (response->success ? "simulated arm move accepted" : "injected arm failure");
      });
    RCLCPP_INFO(get_logger(), "Mock arm only: no hardware commands will be sent");
  }

private:
  using Service = fruit_sorting_interfaces::srv::MoveArm;
  std::string fail_phase_;
  rclcpp::Service<Service>::SharedPtr service_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MockArm>());
  rclcpp::shutdown();
  return 0;
}
