import mesa
import numpy as np
from typing import List, Tuple, Dict, Optional
import random
from enum import Enum


class TrafficLightState(Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class LaneDirection(Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"


class VehicleAgent(mesa.Agent):
    """Agent representing a vehicle with two-lane road system"""

    def __init__(self, unique_id: int, model, spawn_point: Tuple[int, int], lane: int, direction: LaneDirection):
        super().__init__(unique_id, model)
        self.speed = 0
        self.max_speed = 1.0
        self.acceleration = 0.1
        self.deceleration = 0.2
        self.hard_braking = 0.4
        self.safe_distance = 2.0
        self.position = list(spawn_point)
        self.spawn_point = spawn_point
        self.lane = lane
        self.direction = direction
        self.direction_str = direction.value
        self.waiting_time = 0
        self.total_travel_time = 0
        self.stopped = False
        self.color = self._generate_color()

        self.number_of_stops = 0
        self.total_co2_emission = 0.0

        # COPERT coefficients
        self.COPERT = {
            'a': 0.001, 'b': 0.05, 'c': 1.0,
            'd': 0.02, 'e': 0.0005,
        }
        self.SPEED_TO_KMPH = 10.0

        self.waiting_at_light = False
        self.has_passed_light = False

        grid_width = model.grid.width
        grid_height = model.grid.height
        center_x = grid_width // 2
        center_y = grid_height // 2
        lane_offset = 2.0

        if direction == LaneDirection.RIGHT:
            self.start_x = 0
            self.end_x = grid_width - 1
            self.start_y = center_y - lane_offset
            self.end_y = self.start_y
            self.intersection_x = center_x
            self.intersection_y = self.start_y
        elif direction == LaneDirection.LEFT:
            self.start_x = grid_width - 1
            self.end_x = 0
            self.start_y = center_y + lane_offset
            self.end_y = self.start_y
            self.intersection_x = center_x
            self.intersection_y = self.start_y
        elif direction == LaneDirection.DOWN:
            self.start_y = 0
            self.end_y = grid_height - 1
            self.start_x = center_x + lane_offset
            self.end_x = self.start_x
            self.intersection_x = self.start_x
            self.intersection_y = center_y
        else:  # UP
            self.start_y = grid_height - 1
            self.end_y = 0
            self.start_x = center_x - lane_offset
            self.end_x = self.start_x
            self.intersection_x = self.start_x
            self.intersection_y = center_y

        self.position = [self.start_x, self.start_y]

        self.traffic_light = self._find_first_traffic_light(model.traffic_lights)

        self.route = [self.start, self.intersection, self.end]
        self.current_segment = 0

    def _find_first_traffic_light(self, traffic_lights):
        """Find the traffic light that is before the intersection on this vehicle's path"""
        closest_light = None
        min_distance = float('inf')

        for light in traffic_lights:
            if self.direction_str in ["RIGHT", "LEFT"]:
                if light.direction != "horizontal":
                    continue
                if abs(light.position[1] - self.intersection_y) > 3:
                    continue

                if self.direction_str == "RIGHT":
                    if light.position[0] > self.start_x and light.position[0] < self.intersection_x:
                        dist = light.position[0] - self.start_x
                        if dist < min_distance:
                            min_distance = dist
                            closest_light = light
                else:  # LEFT
                    if light.position[0] < self.start_x and light.position[0] > self.intersection_x:
                        dist = self.start_x - light.position[0]
                        if dist < min_distance:
                            min_distance = dist
                            closest_light = light

            else:
                if light.direction != "vertical":
                    continue
                if abs(light.position[0] - self.intersection_x) > 3:
                    continue

                if self.direction_str == "DOWN":
                    if light.position[1] > self.start_y and light.position[1] < self.intersection_y:
                        dist = light.position[1] - self.start_y
                        if dist < min_distance:
                            min_distance = dist
                            closest_light = light
                else:  # UP
                    if light.position[1] < self.start_y and light.position[1] > self.intersection_y:
                        dist = self.start_y - light.position[1]
                        if dist < min_distance:
                            min_distance = dist
                            closest_light = light

        return closest_light

    @property
    def start(self):
        return (self.start_x, self.start_y)

    @property
    def intersection(self):
        return (self.intersection_x, self.intersection_y)

    @property
    def end(self):
        return (self.end_x, self.end_y)

    def _generate_color(self):
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
        return random.choice(colors)

    def _calculate_distance(self, pos1, pos2):
        return np.sqrt((pos2[0] - pos1[0]) ** 2 + (pos2[1] - pos1[1]) ** 2)

    def _get_distance_to_light(self):
        """Calculate distance to traffic light along the path"""
        if not self.traffic_light:
            return float('inf')

        if self.direction_str == "RIGHT":
            return self.traffic_light.position[0] - self.position[0]
        elif self.direction_str == "LEFT":
            return self.position[0] - self.traffic_light.position[0]
        elif self.direction_str == "DOWN":
            return self.traffic_light.position[1] - self.position[1]
        else:  # UP
            return self.position[1] - self.traffic_light.position[1]

    def _has_passed_light(self):
        """Check if vehicle has passed the traffic light"""
        if not self.traffic_light:
            return True

        if self.direction_str == "RIGHT":
            return self.position[0] >= self.traffic_light.position[0]
        elif self.direction_str == "LEFT":
            return self.position[0] <= self.traffic_light.position[0]
        elif self.direction_str == "DOWN":
            return self.position[1] >= self.traffic_light.position[1]
        else:  # UP
            return self.position[1] <= self.traffic_light.position[1]

    def _get_vehicle_ahead(self):
        """Find the vehicle directly ahead on the same lane"""
        if not self.route or self.current_segment >= len(self.route):
            return None

        current_target = self.route[self.current_segment]
        vehicles_ahead = []

        for vehicle in self.model.vehicles:
            if vehicle.unique_id == self.unique_id:
                continue

            if vehicle.lane == self.lane and vehicle.direction_str == self.direction_str:
                if vehicle.current_segment == self.current_segment:
                    dist_self = self._calculate_distance(self.position, current_target)
                    dist_other = self._calculate_distance(vehicle.position, current_target)

                    if dist_other < dist_self:
                        if self.direction_str == "RIGHT":
                            if vehicle.position[0] > self.position[0]:
                                vehicles_ahead.append((dist_other, vehicle))
                        elif self.direction_str == "LEFT":
                            if vehicle.position[0] < self.position[0]:
                                vehicles_ahead.append((dist_other, vehicle))
                        elif self.direction_str == "DOWN":
                            if vehicle.position[1] > self.position[1]:
                                vehicles_ahead.append((dist_other, vehicle))
                        else:  # UP
                            if vehicle.position[1] < self.position[1]:
                                vehicles_ahead.append((dist_other, vehicle))

        if vehicles_ahead:
            vehicles_ahead.sort(key=lambda x: x[0])
            return vehicles_ahead[0][1]
        return None

    def _calculate_safe_speed(self, vehicle_ahead):
        if not vehicle_ahead:
            return self.max_speed

        distance = self._calculate_distance(self.position, vehicle_ahead.position)
        safe_distance = self.safe_distance + self.speed * 2

        if distance < 1.0:
            return 0
        elif distance < safe_distance * 0.5:
            return 0
        elif distance < safe_distance:
            return self.max_speed * (distance / safe_distance)
        else:
            return self.max_speed

    def _copert_co2_emission(self, speed, distance):
        if speed <= 0:
            return 0.02

        v = speed * self.SPEED_TO_KMPH
        numerator = self.COPERT['a'] * v ** 2 + self.COPERT['b'] * v + self.COPERT['c']
        denominator = 1 + self.COPERT['d'] * v + self.COPERT['e'] * v ** 2
        distance_km = distance * 0.1

        if denominator == 0:
            return 0
        return (numerator / denominator) * distance_km

    def move(self):
        """Vehicle movement logic with collision avoidance"""
        was_moving = self.speed > 0

        if not self.route or self.current_segment >= len(self.route):
            return

        target_pos = self.route[self.current_segment]

        if self.traffic_light and self._has_passed_light():
            self.waiting_at_light = False

        vehicle_ahead = self._get_vehicle_ahead()
        safe_speed = self._calculate_safe_speed(vehicle_ahead)

        traffic_light_speed = self.max_speed

        if self.current_segment == 1 and self.traffic_light and not self._has_passed_light():
            dist_to_light = self._get_distance_to_light()

            if dist_to_light > 0 and dist_to_light < 4:
                if self.traffic_light.state == TrafficLightState.RED:
                    self.waiting_at_light = True
                    if dist_to_light < 2.0:
                        traffic_light_speed = 0
                    elif dist_to_light < 8.0:
                        traffic_light_speed = self.max_speed * (dist_to_light / 8.0)
                    else:
                        traffic_light_speed = self.max_speed

                elif self.traffic_light.state == TrafficLightState.YELLOW:
                    if dist_to_light < 4.0:
                        traffic_light_speed = 0
                    else:
                        traffic_light_speed = self.max_speed
                else:  # GREEN
                    self.waiting_at_light = False
                    if dist_to_light < 1.5:
                        traffic_light_speed = self.max_speed
                    else:
                        traffic_light_speed = self.max_speed

        if self.waiting_at_light:
            self.speed = 0
            self.stopped = True
            self.waiting_time += 1
            self.total_travel_time += 1
            return

        desired_speed = min(safe_speed, traffic_light_speed, self.max_speed)

        if desired_speed < self.speed:
            self.speed = max(desired_speed, self.speed - self.deceleration)
        elif desired_speed > self.speed:
            self.speed = min(desired_speed, self.speed + self.acceleration)

        if self.speed < 0.01:
            self.speed = 0.0

        distance_to_target = self._calculate_distance(self.position, target_pos)
        if distance_to_target < 1.0:
            self.current_segment += 1
            if self.current_segment >= len(self.route):
                self.model.vehicle_completed(self)
                return
            target_pos = self.route[self.current_segment]

        if self.speed > 0:
            dx = target_pos[0] - self.position[0]
            dy = target_pos[1] - self.position[1]

            if abs(dx) > 0 or abs(dy) > 0:
                norm = np.sqrt(dx ** 2 + dy ** 2)
                if norm > 0:
                    dx /= norm
                    dy /= norm

                new_x = self.position[0] + dx * self.speed
                new_y = self.position[1] + dy * self.speed
                new_position = (new_x, new_y)

                if not self.model.is_position_occupied((new_x, new_y), self.unique_id):
                    distance_traveled = self._calculate_distance(self.position, (new_x, new_y))
                    self.position = [new_x, new_y]

                    co2 = self._copert_co2_emission(self.speed, distance_traveled)
                    self.total_co2_emission += co2
                else:
                    self.speed = 0

        self.stopped = (self.speed == 0)

        if was_moving and self.stopped:
            self.number_of_stops += 1
            self.waiting_time += 1
        elif self.stopped:
            self.waiting_time += 1
        else:
            self.waiting_time = max(0, self.waiting_time - 1)

        self.total_travel_time += 1

    def step(self):
        self.move()

class TrafficLightAgent(mesa.Agent):
    """Agent representing a traffic light"""

    def __init__(self, unique_id: int, model, position: Tuple[int, int],
                 direction: str, algorithm_type: str = "static"):
        super().__init__(unique_id, model)
        self.position = position
        self.direction = direction
        self.state = TrafficLightState.RED
        self.algorithm_type = algorithm_type
        self.timer = 0
        self.green_duration = 100
        self.yellow_duration = 20
        self.red_duration = 100
        self.max_queue_length = 0
        self.total_vehicles_passed = 0

        self.cycle_counter = 0

    def get_queue_length(self) -> int:
        """Get queue length in front of traffic light"""
        queue = 0
        for agent in self.model.schedule.agents:
            if isinstance(agent, VehicleAgent):
                if self._is_in_queue(agent):
                    queue += 1
        self.max_queue_length = max(self.max_queue_length, queue)
        return int(queue)

    def _is_in_queue(self, vehicle: VehicleAgent) -> bool:
        """Check if vehicle is in queue for this traffic light"""
        if vehicle.stopped:
            if self.direction == "horizontal":
                if abs(vehicle.position[1] - self.position[1]) < 5:
                    if vehicle.direction_str in ["RIGHT", "LEFT"]:
                        return True
            else:
                if abs(vehicle.position[0] - self.position[0]) < 5:
                    if vehicle.direction_str in ["UP", "DOWN"]:
                        return True
        return False

    def static_algorithm(self):
        """Static algorithm with fixed cycle times - opposite lights show same color"""
        self.cycle_counter += 1

        if self.direction == "horizontal":
            if self.cycle_counter <= self.green_duration:
                self.state = TrafficLightState.GREEN
            elif self.cycle_counter <= self.green_duration + self.yellow_duration:
                self.state = TrafficLightState.YELLOW
            else:
                self.state = TrafficLightState.RED

            if self.cycle_counter >= self.green_duration + self.yellow_duration + self.red_duration:
                self.cycle_counter = 0

        else:  # vertical
            if self.cycle_counter <= self.red_duration:
                self.state = TrafficLightState.RED
            elif self.cycle_counter <= self.red_duration + self.green_duration:
                self.state = TrafficLightState.GREEN
            else:
                self.state = TrafficLightState.YELLOW

            if self.cycle_counter >= self.red_duration + self.green_duration + self.yellow_duration:
                self.cycle_counter = 0

    def adaptive_algorithm(self):
        """Adaptive algorithm based on queue length"""
        queue_length = self.get_queue_length()
        if queue_length > 10:
            self.green_duration = 40
            self.red_duration = 20
        elif queue_length > 5:
            self.green_duration = 30
            self.red_duration = 30
        else:
            self.green_duration = 20
            self.red_duration = 40
        self.static_algorithm()

    def step(self):
        """Main simulation step for traffic light"""
        if self.algorithm_type == "static":
            self.static_algorithm()
        elif self.algorithm_type == "adaptive":
            self.adaptive_algorithm()
        elif self.algorithm_type == "coordinated":
            self.adaptive_algorithm()

        if self.state == TrafficLightState.GREEN:
            passing = self._count_passing_vehicles()
            self.total_vehicles_passed += passing

    def _count_passing_vehicles(self) -> int:
        """Count vehicles passing through traffic light"""
        count = 0
        for agent in self.model.schedule.agents:
            if isinstance(agent, VehicleAgent):
                if self._is_passing(agent):
                    count += 1
        return count

    def _is_passing(self, vehicle: VehicleAgent) -> bool:
        """Check if vehicle is passing through traffic light"""
        distance = np.sqrt((vehicle.position[0] - self.position[0]) ** 2 +
                           (vehicle.position[1] - self.position[1]) ** 2)
        return distance < 3 and not vehicle.stopped

    def get_state_dict(self) -> Dict:
        """Get state as dictionary for API"""
        return {
            "id": int(self.unique_id),
            "x": float(self.position[0]),
            "y": float(self.position[1]),
            "state": str(self.state.value),
            "queue_length": self.get_queue_length(),
            "direction": str(self.direction),
            "green_duration": int(self.green_duration),
            "max_queue": int(self.max_queue_length),
            "total_passed": int(self.total_vehicles_passed)
        }