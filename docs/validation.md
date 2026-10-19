# 验证记录

日期：2026-10-19。

## 验证环境

- 云宿主机为 Debian 13；未向宿主机安装 Ubuntu/ROS 软件包。
- 使用官方 `ros:humble-ros-base-jammy` 容器，Ubuntu 22.04.5、Python 3.10、GCC 11。
- 固定镜像摘要：`sha256:566b87e6dfc48392189a9c32e594e84060fa9948de93b04e536f39475a1f6963`。
- 当前仓库挂载进容器，实际执行仓库内的依赖、构建和测试脚本。
- rosdep 通过标准 `SSL_CERT_FILE` 使用平台信任的 CA，保持 TLS 校验。最终构建/测试使用 CI 相同的 `ROS_DOMAIN_ID=42`，并清空 `XML_CATALOG_FILES`，验证不依赖先前环境的本地 XML catalog。

## 结果

| 检查 | 结果 |
| --- | --- |
| `scripts/install_dependencies.sh` | 通过，rosdep 更新成功，全部声明的依赖已满足 |
| `colcon build` | 4 个功能包构建成功，包括 rosidl 生成的 Python/C++ 接口与两个 C++ 节点 |
| 感知单元测试 | 3 个通过 |
| 规划策略单元测试 | 27 个通过 |
| 启动集成测试 | 1 个通过，实际启动完整模拟流水线及故障测试实例 |
| 进程退出测试 | 1 个通过，所有启动的 ROS 节点正常退出 |
| `colcon test-result --verbose` | 汇总 34 项，0 错误、0 失败、0 跳过 |

上面的独立测试用例为 32 个；colcon 汇总还包括 CTest 包装项，因此报告为 34，不能把包装项当成额外业务测试。

端到端验证包括：

- 苹果、番茄、黄瓜分别生成目标并全部返回模拟完成；目标投放位置匹配类别配置。
- 未知类、低置信度检测没有生成目标；重复检测不重复执行。
- 不同命名空间的测试流水线互不干扰。
- 真实 C++ mock 服务拒绝空的非法请求。
- 受控测试服务记录 `arm/pick → hand/close → arm/place → hand/open` 的调用顺序。
- 机械臂或手部服务失败后不会继续当前目标的后续步骤。
- 拒绝 `simulated=false` 的响应。
- 响应超时与服务不可用产生明确失败结果；晚到的响应不会导致后续步骤继续执行。

## 诊断与限制

- 初次依赖安装尝试遇到云代理对 `packages.ros.org` 的拒绝，以及容器缺少云代理 CA。已通过平台可信 CA 恢复 HTTPS 验证；基础镜像已具备全部所需 apt 包，安装脚本在依赖满足时无需更新 apt。依赖刷新已验证成功，新增缺失 ROS deb 包时仍需网络策略允许 `packages.ros.org`。
- GitHub Actions 工作流已配置；本记录是当前云实例中 Ubuntu/Humble 容器的实测结果，远端 CI 状态请以 GitHub Actions 实际运行为准。
- 未验证真实视觉、机器人轨迹、物理抓取、碰撞、Gazebo 或真实硬件；这些功能尚未实现。
- 当前维护者邮箱为模板占位信息。没有假设真实机器人型号、驱动协议、运动学参数或抓取力。

复现入口：仓库根目录的 `./scripts/install_dependencies.sh` 和 `./scripts/build_and_test.sh`，执行环境必须是 Ubuntu 22.04 / Humble。
