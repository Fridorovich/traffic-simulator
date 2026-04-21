# network_vehicle.py

from typing import List, Tuple, Optional
import numpy as np
import random
from ..agents import VehicleAgent, LaneDirection, TrafficLightState


class NetworkVehicleAgent(VehicleAgent):
    """Vehicle that follows a precomputed path through the road network"""

    def __init__(self, unique_id: int, model, spawn_point: Tuple[float, float],
                 lane: int, direction: LaneDirection, network, destination: Tuple[float, float]):
        super().__init__(unique_id, model, spawn_point, lane, direction)
        self.network = network
        self.final_destination = destination

        # Find start and end intersections
        self.start_intersection = self._find_closest_intersection(spawn_point)
        self.end_intersection = self._find_closest_intersection(destination)

        print(f"\n=== NEW VEHICLE {unique_id} ===")
        print(f"Spawn point: {spawn_point}")
        print(f"Initial direction: {direction}")
        print(
            f"Start intersection: {self.start_intersection.id} ({self.start_intersection.x}, {self.start_intersection.y})")
        print(f"End intersection: {self.end_intersection.id} ({self.end_intersection.x}, {self.end_intersection.y})")

        # Initialize default values
        self.current_road = None
        self.current_direction_str = direction.value
        self.traffic_light = None
        self.current_target_index = 0
        self.path = None

        # Find path using A*
        if self.start_intersection.id != self.end_intersection.id:
            self.path = self._find_path()

        if self.path and len(self.path) > 1:
            print(f"Path found: {self.path}")
            self.current_target_index = 1
            self._update_target()
        else:
            print("No path found - going directly to destination")
            self.current_target = destination
            self.traffic_light = None
            self.current_road = None

        # State flags
        self.waiting_at_light = False

    def _find_closest_intersection(self, point: Tuple[float, float]):
        """Find the closest intersection to a point"""
        min_dist = float('inf')
        closest = None
        for node in self.network.intersections.values():
            dist = ((node.x - point[0]) ** 2 + (node.y - point[1]) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                closest = node
        return closest

    def _find_path(self):
        """Find path from start to end intersection using A*"""
        if not self.start_intersection or not self.end_intersection:
            return None

        # Use PathFinder
        path = self.network.path_finder.find_path(
            self.start_intersection.id,
            self.end_intersection.id
        )
        return path

    def _get_road_between(self, from_id: int, to_id: int):
        """Get road segment between two intersections"""
        for road in self.network.roads:
            if road.from_node.id == from_id and road.to_node.id == to_id:
                return road
        return None

    def _get_traffic_light_for_road(self, road):
        """Get traffic light at the end of the road"""
        if road:
            return road.to_node.get_traffic_light_for_direction(road.direction)
        return None

    def _update_target(self):
        """Update current target to next point in path"""
        if self.current_target_index < len(self.path):
            current_node_id = self.path[self.current_target_index - 1]
            next_node_id = self.path[self.current_target_index]

            self.current_intersection = self.network.get_intersection(current_node_id)
            self.target_intersection = self.network.get_intersection(next_node_id)

            # Get road and determine direction
            self.current_road = self._get_road_between(current_node_id, next_node_id)
            if self.current_road:
                # current_direction is a string from road.direction
                self.current_direction_str = self.current_road.direction
                self.direction_str = self.current_road.direction
                # Also update direction as LaneDirection enum for compatibility
                if self.current_road.direction == "RIGHT":
                    self.direction = LaneDirection.RIGHT
                elif self.current_road.direction == "LEFT":
                    self.direction = LaneDirection.LEFT
                elif self.current_road.direction == "DOWN":
                    self.direction = LaneDirection.DOWN
                else:  # UP
                    self.direction = LaneDirection.UP
                self.traffic_light = self._get_traffic_light_for_road(self.current_road)

            self.current_target = (self.target_intersection.x, self.target_intersection.y)

            print(
                f"  Target {self.current_target_index}: go to intersection {next_node_id} ({self.current_target[0]}, {self.current_target[1]}) direction {self.current_direction_str}")
        else:
            # Last segment - go to final destination
            self.current_target = self.final_destination
            self.traffic_light = None
            self.current_road = None
            print(f"  Final target: ({self.current_target[0]}, {self.current_target[1]})")

    def _advance_to_next_target(self):
        """Move to next point in the path"""
        self.current_target_index += 1

        if self.path and self.current_target_index < len(self.path):
            self._update_target()
        else:
            # Reached final intersection, now go to destination
            self.current_target = self.final_destination
            self.traffic_light = None
            self.current_road = None
            print(
                f"  Reached final intersection, going to destination ({self.current_target[0]}, {self.current_target[1]})")

    def _get_distance_to_target(self):
        """Get distance to current target"""
        return self._calculate_distance(self.position, self.current_target)

    def move(self):
        """Movement logic following precomputed path"""
        was_moving = self.speed > 0

        # Check if reached current target
        distance_to_target = self._get_distance_to_target()

        if distance_to_target < 1.0:
            # Check if reached final destination
            if self.current_target == self.final_destination:
                print(f"Vehicle {self.unique_id} reached final destination!")
                self.model.vehicle_completed(self)
                return

            # Reached an intersection - advance to next target
            self._advance_to_next_target()
            return

        # Get vehicle ahead on same road (only if we have a road)
        vehicle_ahead = None
        safe_speed = self.max_speed

        if self.current_road:
            vehicle_ahead = self._get_vehicle_ahead()
            safe_speed = self._calculate_safe_speed(vehicle_ahead)

        # Traffic light influence
        traffic_light_speed = self.max_speed
        if self.traffic_light and self.current_target != self.final_destination:
            dist_to_light = self._calculate_distance(self.position, self.traffic_light.position)

            if dist_to_light < 15:
                if self.traffic_light.state == TrafficLightState.RED:
                    self.waiting_at_light = True
                    if dist_to_light < 2.0:
                        traffic_light_speed = 0
                    elif dist_to_light < 8.0:
                        traffic_light_speed = self.max_speed * (dist_to_light / 8.0)
                elif self.traffic_light.state == TrafficLightState.YELLOW:
                    if dist_to_light < 4.0:
                        traffic_light_speed = 0
                else:
                    self.waiting_at_light = False

        # If waiting at red light, stop
        if self.waiting_at_light:
            self.speed = 0
            self.stopped = True
            self.waiting_time += 1
            self.total_travel_time += 1
            return

        # Calculate desired speed
        desired_speed = min(safe_speed, traffic_light_speed, self.max_speed)

        # Adjust speed
        if desired_speed < self.speed:
            self.speed = max(desired_speed, self.speed - self.deceleration)
        elif desired_speed > self.speed:
            self.speed = min(desired_speed, self.speed + self.acceleration)

        if self.speed < 0.01:
            self.speed = 0.0

        # Move towards target
        if self.speed > 0:
            old_position = self.position.copy()

            dx = self.current_target[0] - self.position[0]
            dy = self.current_target[1] - self.position[1]

            if abs(dx) > 0 or abs(dy) > 0:
                norm = np.sqrt(dx ** 2 + dy ** 2)
                if norm > 0:
                    dx /= norm
                    dy /= norm

                new_x = self.position[0] + dx * self.speed
                new_y = self.position[1] + dy * self.speed

                # Don't go past traffic light
                if self.traffic_light and self.current_target != self.final_destination:
                    dist_to_light = self._calculate_distance((new_x, new_y), self.traffic_light.position)
                    if dist_to_light < 0.5 and self.traffic_light.state != TrafficLightState.GREEN:
                        if self.direction_str == "RIGHT":
                            new_x = self.traffic_light.position[0] - 0.5
                        elif self.direction_str == "LEFT":
                            new_x = self.traffic_light.position[0] + 0.5
                        elif self.direction_str == "DOWN":
                            new_y = self.traffic_light.position[1] - 0.5
                        else:  # UP
                            new_y = self.traffic_light.position[1] + 0.5
                        self.speed = 0

                # Collision check
                if not self.model.is_position_occupied((new_x, new_y), self.unique_id):
                    distance = self._calculate_distance(self.position, (new_x, new_y))
                    self.position = [new_x, new_y]

                    # Calculate CO2
                    co2 = self._copert_co2_emission(self.speed, distance)
                    self.total_co2_emission += co2
                else:
                    self.speed = 0

        # Update state
        self.stopped = (self.speed == 0)

        if was_moving and self.stopped:
            self.number_of_stops += 1
            self.waiting_time += 1
        elif self.stopped:
            self.waiting_time += 1
        else:
            self.waiting_time = max(0, self.waiting_time - 1)

        self.total_travel_time += 1

    def _get_vehicle_ahead(self):
        """Find vehicle ahead on same road segment"""
        vehicles_ahead = []

        for vehicle in self.model.vehicles:
            if vehicle.unique_id == self.unique_id:
                continue

            # Check if vehicle is on same path segment
            if (hasattr(vehicle, 'current_road') and
                    vehicle.current_road == self.current_road and
                    hasattr(vehicle, 'current_target_index') and
                    vehicle.current_target_index == self.current_target_index):

                if self.direction_str in ["RIGHT", "LEFT"]:
                    if self.direction_str == "RIGHT":
                        if vehicle.position[0] > self.position[0]:
                            distance = vehicle.position[0] - self.position[0]
                            vehicles_ahead.append((distance, vehicle))
                    else:
                        if vehicle.position[0] < self.position[0]:
                            distance = self.position[0] - vehicle.position[0]
                            vehicles_ahead.append((distance, vehicle))
                else:
                    if self.direction_str == "DOWN":
                        if vehicle.position[1] > self.position[1]:
                            distance = vehicle.position[1] - self.position[1]
                            vehicles_ahead.append((distance, vehicle))
                    else:
                        if vehicle.position[1] < self.position[1]:
                            distance = self.position[1] - vehicle.position[1]
                            vehicles_ahead.append((distance, vehicle))

        if vehicles_ahead:
            vehicles_ahead.sort(key=lambda x: x[0])
            return vehicles_ahead[0][1]
        return None

    def _calculate_safe_speed(self, vehicle_ahead):
        if not vehicle_ahead:
            return self.max_speed

        distance = self._calculate_distance(self.position, vehicle_ahead.position)
        safe_distance = self.safe_distance + self.speed * 1.5

        if distance < 0.5:
            return 0.0
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

    def step(self):
        self.move()