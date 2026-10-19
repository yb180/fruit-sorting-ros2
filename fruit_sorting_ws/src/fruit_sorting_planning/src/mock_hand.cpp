#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "fruit_sorting_interfaces/srv/command_hand.hpp"

class MockHand : public rclcpp::Node
{
public:
  MockHand() : Node("mock_hand")
  {
    fail_command_ = declare_parameter<std::string>("fail_command", "");
    service_ = create_service<Service>("hand/command",
      [this](const std::shared_ptr<Service::Request> request,
      std::shared_ptr<Service::Response> response) {
        const bool valid = !request->target_id.empty() && !request->class_label.empty() &&
          (request->command == "close" || request->command == "open");
        response->simulated = true;
        response->success = valid && request->command != fail_command_;
        response->message = !valid ? "invalid mock hand request" :
          (response->success ? "simulated hand command accepted" : "injected hand failure");
      });
    RCLCPP_INFO(get_logger(), "Mock hand only: no hardware commands will be sent");
  }

private:
  using Service = fruit_sorting_interfaces::srv::CommandHand;
  std::string fail_command_;
  rclcpp::Service<Service>::SharedPtr service_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MockHand>());
  rclcpp::shutdown();
  return 0;
}
