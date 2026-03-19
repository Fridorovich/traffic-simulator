import mesa
import numpy as np
from typing import List, Tuple, Dict, Optional
import random
from enum import Enum


class TrafficLightState(Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class VehicleAgent(mesa.Agent):
    """Agent representing a vehicle"""

    def __init__(self, unique_id: int, model, spawn_point: Tuple[int, int]):
        super().__init__(unique_id, model)
        self.speed = 0
        self.max_speed = 1.0
        self.acceleration = 0.1
        self.deceleration = 0.2
        self.position = spawn_point
        self.spawn_point = spawn_point
        self.waiting_time = 0
        self.total_travel_time = 0
        self.stopped = False
        self.color = self._generate_color()
        self.destination = self._generate_destination(spawn_point)
        self.route = self._calculate_route(spawn_point, self.destination)
        self.current_segment = 0

        self.number_of_stops = 0
        self.was_stopped_last_step = False
        self.total_co2_emission = 0.0

        # COPERT coefficients for average passenger car (gasoline, Euro 4)
        self.COPERT = {
            'a': 0.001,  # v² coefficient
            'b': 0.05,  # v coefficient
            'c': 1.0,  # constant
            'd': 0.02,  # denominator v coefficient
            'e': 0.0005,  # denominator v² coefficient
        }

        # Conversion factor: our speed units to km/h (approximate)
        self.SPEED_TO_KMPH = 10.0

    def _generate_color(self):
        """Generate random color for vehicle"""
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
        return random.choice(colors)

    def _generate_destination(self, spawn_point: Tuple[int, int]) -> Tuple[int, int]:
        """Generate random destination point"""
        grid_width = self.model.grid.width
        grid_height = self.model.grid.height

        destinations = []

        if spawn_point[0] == 0:
            destinations = [(grid_width - 1, spawn_point[1]),
                            (spawn_point[0], grid_height - 1),
                            (spawn_point[0], 0)]
        elif spawn_point[0] == grid_width - 1:
            destinations = [(0, spawn_point[1]),
                            (spawn_point[0], grid_height - 1),
                            (spawn_point[0], 0)]
        elif spawn_point[1] == 0:
            destinations = [(spawn_point[0], grid_height - 1),
                            (0, spawn_point[1]),
                            (grid_width - 1, spawn_point[1])]
        elif spawn_point[1] == grid_height - 1:
            destinations = [(spawn_point[0], 0),
                            (0, spawn_point[1]),
                            (grid_width - 1, spawn_point[1])]

        return random.choice(destinations) if destinations else spawn_point

    def _calculate_route(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Calculate route through intersection center"""
        center_x = self.model.grid.width // 2
        center_y = self.model.grid.height // 2

        return [start, (center_x, center_y), end]

    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two positions"""
        return np.sqrt((pos2[0] - pos1[0]) ** 2 + (pos2[1] - pos1[1]) ** 2)

    def _copert_co2_emission(self, speed: float, distance: float) -> float:
        """
        Calculate CO2 emission using COPERT formula

        CO2 [g] = (a*v² + b*v + c) / (1 + d*v + e*v²) * distance

        Args:
            speed: Vehicle speed in our units
            distance: Distance traveled in our units

        Returns:
            CO2 emission in grams
        """
        if speed <= 0:
            return 0.02  # Average idle emission per step in grams

        # Convert speed to km/h for realistic formula
        v = speed * self.SPEED_TO_KMPH

        # COPERT formula
        numerator = self.COPERT['a'] * v ** 2 + self.COPERT['b'] * v + self.COPERT['c']
        denominator = 1 + self.COPERT['d'] * v + self.COPERT['e'] * v ** 2

        # Convert distance to km (assuming our units to km conversion)
        distance_km = distance * 0.1  # Rough conversion: 1 unit = 0.1 km

        if denominator == 0:
            return 0

        co2_per_km = numerator / denominator  # g/km
        return co2_per_km * distance_km

    def move(self):
        """Vehicle movement logic with stop tracking"""
        is_stopped_now = (self.speed == 0)

        if not self.was_stopped_last_step and is_stopped_now:
            self.number_of_stops += 1
            # print(f"Vehicle {self.unique_id} stopped! Total stops: {self.number_of_stops}")

        if not self.route or self.current_segment >= len(self.route):
            return

        target_pos = self.route[self.current_segment]

        distance_to_target = self._calculate_distance(self.position, target_pos)

        if distance_to_target < 1.0:
            self.current_segment += 1
            if self.current_segment >= len(self.route):
                self.model.vehicle_completed(self)
                return
            target_pos = self.route[self.current_segment]

        if self.current_segment == 1:
            traffic_light = self.model.get_traffic_light_for_vehicle(self)
            if traffic_light:
                dist_to_light = self._calculate_distance(self.position, traffic_light.position)

                if dist_to_light < 8 and traffic_light.state != TrafficLightState.GREEN:
                    self.speed = max(0, self.speed - self.deceleration)
                    if self.speed == 0:
                        self.stopped = True
                        self.waiting_time += 1
                        self.total_co2_emission += self._copert_co2_emission(0, 0)

                    self.was_stopped_last_step = (self.speed == 0)
                    return
                else:
                    self.stopped = False
                    if self.speed > 0:
                        self.waiting_time = max(0, self.waiting_time - 1)

        # Movement calculation
        dx = target_pos[0] - self.position[0]
        dy = target_pos[1] - self.position[1]

        if abs(dx) > 0 or abs(dy) > 0:
            norm = np.sqrt(dx ** 2 + dy ** 2)
            if norm > 0:
                dx /= norm
                dy /= norm

            self.speed = min(self.max_speed, self.speed + self.acceleration)

            new_x = self.position[0] + dx * self.speed
            new_y = self.position[1] + dy * self.speed
            new_position = (new_x, new_y)

            # Calculate distance traveled this step
            distance_traveled = self._calculate_distance(self.position, new_position)

            if not self.model.is_position_occupied(new_position, self.unique_id):
                self.position = new_position

                # Calculate CO2 for this movement using COPERT
                co2_emission = self._copert_co2_emission(self.speed, distance_traveled)
                self.total_co2_emission += co2_emission

        self.total_travel_time += 1
        self.was_stopped_last_step = (self.speed == 0)

    def step(self):
        self.move()

    def get_environmental_metrics(self):
        """Get environmental metrics for this vehicle"""
        return {
            "number_of_stops": self.number_of_stops,
            "total_co2_g": round(self.total_co2_emission, 2),
            "total_co2_kg": round(self.total_co2_emission / 1000, 3),
        }


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
        self.green_duration = 30
        self.yellow_duration = 5
        self.red_duration = 35
        self.max_queue_length = 0
        self.total_vehicles_passed = 0

        self.cycle_start_offset = random.randint(0, 60)

    def get_queue_length(self) -> int:
        """Get queue length in front of traffic light"""
        queue = 0
        for agent in self.model.schedule.agents:
            if isinstance(agent, VehicleAgent):
                if self._is_in_queue(agent):
                    queue += 1
        self.max_queue_length = max(self.max_queue_length, queue)
        return queue

    def _is_in_queue(self, vehicle: VehicleAgent) -> bool:
        """Check if vehicle is in queue for this traffic light"""
        if vehicle.stopped:
            if self.direction == "horizontal":
                if abs(vehicle.position[1] - self.position[1]) < 5:
                    if (self.position[0] > vehicle.position[0] and
                            vehicle.destination[0] > vehicle.position[0]):
                        return True
                    elif (self.position[0] < vehicle.position[0] and
                          vehicle.destination[0] < vehicle.position[0]):
                        return True
            else:
                if abs(vehicle.position[0] - self.position[0]) < 5:
                    if (self.position[1] > vehicle.position[1] and
                            vehicle.destination[1] > vehicle.position[1]):
                        return True
                    elif (self.position[1] < vehicle.position[1] and
                          vehicle.destination[1] < vehicle.position[1]):
                        return True
        return False

    def static_algorithm(self):
        """Static algorithm with fixed cycle times"""
        total_cycle = self.green_duration + self.yellow_duration + self.red_duration

        cycle_time = (self.model.schedule.steps + self.cycle_start_offset) % total_cycle

        if self.direction == "horizontal":
            if cycle_time < self.green_duration:
                self.state = TrafficLightState.GREEN
            elif cycle_time < self.green_duration + self.yellow_duration:
                self.state = TrafficLightState.YELLOW
            else:
                self.state = TrafficLightState.RED
        else:
            offset = self.green_duration + self.yellow_duration
            vertical_cycle_time = (cycle_time + offset) % total_cycle

            if vertical_cycle_time < self.green_duration:
                self.state = TrafficLightState.GREEN
            elif vertical_cycle_time < self.green_duration + self.yellow_duration:
                self.state = TrafficLightState.YELLOW
            else:
                self.state = TrafficLightState.RED

        self.timer += 1

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
            "id": self.unique_id,
            "x": self.position[0],
            "y": self.position[1],
            "state": self.state.value,
            "queue_length": self.get_queue_length(),
            "direction": self.direction,
            "green_duration": self.green_duration,
            "max_queue": self.max_queue_length,
            "total_passed": self.total_vehicles_passed
        }