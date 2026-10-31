import json
import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from openai import OpenAI


class AIPlanner(Node):
    def __init__(self):
        super().__init__('ai_planner')
        self.publisher = self.create_publisher(String, '/ai_plan', 10)
        self.client = OpenAI()
        self.model = os.getenv('OPENAI_MODEL', 'gpt-6-luna')

    def create_plan(self, user_instruction):
        prompt = f"""
You are a planner for a mobile robot.

Available waypoints:
START
A
B
C

Convert the user's instruction into a route.
Return ONLY valid JSON in this exact format:
{{"waypoints":["A","C","START"]}}

Do not include explanations.
Do not invent waypoint names.

User instruction:
{user_instruction}
"""

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        text = response.output_text.strip()
        plan = json.loads(text)

        if 'waypoints' not in plan or not isinstance(plan['waypoints'], list):
            raise ValueError('Response must contain a waypoints list')

        valid_points = {'START', 'A', 'B', 'C'}
        for waypoint in plan['waypoints']:
            if waypoint not in valid_points:
                raise ValueError(f'Invalid waypoint: {waypoint}')

        return plan

    def run(self):
        instruction = input('Robot instruction: ')

        try:
            plan = self.create_plan(instruction)
            self.get_logger().info(f'AI plan: {plan}')

            msg = String()
            msg.data = json.dumps(plan)
            self.publisher.publish(msg)

            self.get_logger().info('Plan published to /ai_plan')

        except Exception as exc:
            self.get_logger().error(f'Planning failed: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = AIPlanner()
    node.run()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
