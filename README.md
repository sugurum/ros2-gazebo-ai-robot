# ROS 2 + Gazebo AI Robot

Natural-language task planning with a generative AI model, combined with ROS 2 feedback control in Gazebo.

## Overview

The user gives a natural-language instruction such as:

> Aに行って、そのあとCに寄って、最後にスタート地点に戻って

The AI planner converts the instruction into a JSON waypoint plan:

```json
{"waypoints":["A","C","START"]}
```

The plan is published to `/ai_plan`. A ROS 2 controller then uses Gazebo odometry to continuously calculate the distance and heading error to the next waypoint and publishes velocity commands to the simulated differential-drive robot.

```text
Natural-language instruction
          |
          v
Generative AI inference
          |
          v
JSON waypoint plan
          |
          v
ROS 2 /ai_plan
          |
          v
Waypoint controller <--- /odometry
          |
          v
       /cmd_vel
          |
          v
     ros_gz_bridge
          |
          v
        Gazebo
```

The AI is responsible for high-level task planning. ROS 2 is responsible for low-level robot control. This separation avoids asking the language model to directly choose motor velocities.

## Environment used

- Ubuntu 24.04 ARM64
- ROS 2 Jazzy
- Gazebo Harmonic
- Python 3.12
- `ros_gz_bridge`
- OpenAI Python SDK

The project was developed in an Ubuntu virtual machine on an Apple Silicon Mac using UTM.

## Waypoints

| Name | Coordinate |
| --- | --- |
| START | `(0.0, 0.0)` |
| A | `(2.0, 0.0)` |
| B | `(2.0, 2.0)` |
| C | `(0.0, 2.0)` |

## Setup

Install the ROS / Gazebo integration and Python dependency in your Ubuntu ROS 2 environment:

```bash
sudo apt update
sudo apt install ros-jazzy-ros-gz
python3 -m pip install --user --break-system-packages openai
```

Place the `ai_robot` package in a ROS 2 workspace, for example:

```text
~/ai_robot_ws/src/ai_robot
```

Then build:

```bash
cd ~/ai_robot_ws
colcon build --packages-select ai_robot
source install/setup.bash
```

## API key

Do not put an API key in the source code or commit it to GitHub.

Set it only in the shell environment:

```bash
export OPENAI_API_KEY='YOUR_API_KEY'
```

The model can also be changed with:

```bash
export OPENAI_MODEL='gpt-6-luna'
```

## Run

### Terminal 1: Gazebo

```bash
source /opt/ros/jazzy/setup.bash
gz sim diff_drive.sdf
```

Start the simulation with the Play button in Gazebo.

### Terminal 2: ROS 2 / Gazebo bridge

```bash
source /opt/ros/jazzy/setup.bash
ros2 run ros_gz_bridge parameter_bridge \
/model/vehicle_blue/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist \
/model/vehicle_blue/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry
```

This bridges velocity commands from ROS 2 to Gazebo and odometry from Gazebo to ROS 2.

### Terminal 3: Waypoint controller

```bash
cd ~/ai_robot_ws
source install/setup.bash
ros2 run ai_robot simple_controller
```

The controller should print:

```text
Waiting for a plan on /ai_plan
```

### Terminal 4: AI planner

```bash
cd ~/ai_robot_ws
source install/setup.bash
ros2 run ai_robot ai_planner
```

Example instruction:

```text
Aに行って、そのあとCに寄って、最後にスタート地点に戻って
```

Example generated plan:

```text
AI plan: {'waypoints': ['A', 'C', 'START']}
Plan published to /ai_plan
```

The robot then travels through the requested waypoints using odometry-based feedback control.

## Control method

For each target waypoint, the controller calculates:

```text
dx = target_x - current_x
dy = target_y - current_y

distance = sqrt(dx^2 + dy^2)
target_angle = atan2(dy, dx)
angle_error = target_angle - current_yaw
```

If the heading error is large, the robot rotates in place. Once the robot approximately faces the target, it drives forward while continuing to correct its heading. A waypoint is considered reached when the robot is within 0.2 m of the target.

## AI usage

No additional model training is performed in this project. A pretrained generative AI model is used for inference only.

The model receives a natural-language instruction and converts it into a structured sequence of valid waypoint names. The controller validates the waypoint names before executing the plan.

## Safety / design choice

The language model does not directly generate wheel speeds or `/cmd_vel` values. It only produces a high-level plan. The deterministic ROS 2 controller handles robot motion and validates all waypoint names before execution.

## Demo flow

1. Start Gazebo.
2. Start `ros_gz_bridge`.
3. Start `simple_controller` and wait for a plan.
4. Start `ai_planner` and enter a natural-language command.
5. Confirm the generated waypoint plan in the terminal.
6. Watch the robot execute the route in Gazebo.
