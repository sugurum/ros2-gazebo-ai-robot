import json
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import String


class SimpleController(Node):
    def __init__(self):
        super().__init__('simple_controller')

        self.publisher = self.create_publisher(
            Twist,
            '/model/vehicle_blue/cmd_vel',
            10,
        )

        self.odom_subscription = self.create_subscription(
            Odometry,
            '/model/vehicle_blue/odometry',
            self.odom_callback,
            10,
        )

        self.plan_subscription = self.create_subscription(
            String,
            '/ai_plan',
            self.plan_callback,
            10,
        )

        self.waypoint_map = {
            'START': (0.0, 0.0),
            'A': (2.0, 0.0),
            'B': (2.0, 2.0),
            'C': (0.0, 2.0),
        }

        self.waypoints = []
        self.current_target = 0
        self.active = False

        self.get_logger().info('Waiting for a plan on /ai_plan')

    def plan_callback(self, msg):
        try:
            plan = json.loads(msg.data)
            names = plan['waypoints']

            if not isinstance(names, list) or not names:
                raise ValueError('waypoints must be a non-empty list')

            new_waypoints = []
            for name in names:
                if name not in self.waypoint_map:
                    self.get_logger().error(f'Unknown waypoint: {name}')
                    return
                new_waypoints.append(self.waypoint_map[name])

            self.waypoints = new_waypoints
            self.current_target = 0
            self.active = True
            self.get_logger().info(f'New plan received: {names}')

        except Exception as exc:
            self.get_logger().error(f'Invalid plan: {exc}')

    @staticmethod
    def quaternion_to_yaw(q):
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    @staticmethod
    def normalize_angle(angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def odom_callback(self, msg):
        cmd = Twist()

        if not self.active:
            self.publisher.publish(cmd)
            return

        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        yaw = self.quaternion_to_yaw(msg.pose.pose.orientation)

        target_x, target_y = self.waypoints[self.current_target]
        dx = target_x - x
        dy = target_y - y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        target_angle = math.atan2(dy, dx)
        angle_error = self.normalize_angle(target_angle - yaw)

        if distance < 0.2:
            self.get_logger().info(
                f'Waypoint reached: ({target_x:.1f}, {target_y:.1f})'
            )
            self.current_target += 1

            if self.current_target >= len(self.waypoints):
                self.active = False
                self.publisher.publish(Twist())
                self.get_logger().info('Plan completed!')
            return

        if abs(angle_error) > 0.25:
            cmd.angular.z = angle_error
        else:
            cmd.linear.x = min(0.6, 0.5 * distance)
            cmd.angular.z = angle_error

        self.publisher.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = SimpleController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
