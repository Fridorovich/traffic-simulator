from typing import List, Tuple, Optional
import numpy as np
from ..agents import VehicleAgent, LaneDirection, TrafficLightState


class NetworkVehicleAgent(VehicleAgent):
    """Vehicle that navigates through multiple intersections"""

    def __init__(self, unique_id: int, model, spawn_point: Tuple[float, float],
                 lane: int, direction: LaneDirection, network, destination: Tuple[float, float]):
        super().__init__(unique_id, model, spawn_point, lane, direction)
        self.network = network
        self.destination = destination

        # Find start and end intersections
        self.start_intersection = self._find_closest_intersection(spawn_point)
        self.end_intersection = self._find_closest_intersection(destination)

        # Find path through network
        self.path = self._find_path()

        if self.path and len(self.path) > 1:
            self.current_target_index = 1  # Next intersection to go to
            self.current_target = self._get_intersection_position(self.path[self.current_target_index])
            self.current_road = self._get_road_between(self.path[0], self.path[1])
            self.traffic_light = self.current_road.get_traffic_light_for_entry() if self.current_road else None
        else:
            # Direct path (no intersections in between)
            self.current_target = destination
            self.traffic_light = None

        self.current_segment = 0  # 0 = moving to intersection, 1 = after intersection
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
        """Find path from start to end intersection"""
        if not self.start_intersection or not self.end_intersection:
            return None

        # Simple BFS path finding
        from collections import deque
        queue = deque([(self.start_intersection.id, [self.start_intersection.id])])
        visited = {self.start_intersection.id}

        while queue:
            node_id, path = queue.popleft()

            if node_id == self.end_intersection.id:
                return path

            for neighbor_id in self.network.get_neighbors(node_id):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        return None

    def _get_intersection_position(self, intersection_id: int) -> Tuple[float, float]:
        """Get position of intersection by ID"""
        node = self.network.get_intersection(intersection_id)
        return (node.x, node.y) if node else (0, 0)

    def _get_road_between(self, from_id: int, to_id: int):
        """Get road segment between two intersections"""
        for road in self.network.roads:
            if road.from_node.id == from_id and road.to_node.id == to_id:
                return road
        return None

    def _get_distance_to_target(self):
        """Get distance to current target"""
        return self._calculate_distance(self.position, self.current_target)

    def move(self):
        """Movement logic for network vehicle"""
        was_moving = self.speed > 0

        # Check if reached current target
        distance_to_target = self._get_distance_to_target()

        if distance_to_target < 1.0:
            # Reached current target (intersection or destination)
            if self.current_segment == 0:
                # At intersection, move to next segment
                self.current_segment = 1

                # Move to next intersection in path
                if self.current_target_index < len(self.path) - 1:
                    self.current_target_index += 1
                    self.current_target = self._get_intersection_position(self.path[self.current_target_index])
                    self.current_road = self._get_road_between(
                        self.path[self.current_target_index - 1],
                        self.path[self.current_target_index]
                    )
                    self.traffic_light = self.current_road.get_traffic_light_for_entry() if self.current_road else None
                    self.current_segment = 0  # Start approaching next intersection
                else:
                    # Reached final destination
                    self.model.vehicle_completed(self)
                    return
            else:
                # Reached final destination
                self.model.vehicle_completed(self)
                return

        # Check vehicle ahead
        vehicle_ahead = self._get_vehicle_ahead()
        safe_speed = self._calculate_safe_speed(vehicle_ahead)

        # Traffic light influence (only when approaching intersection)
        traffic_light_speed = self.max_speed
        if self.current_segment == 0 and self.traffic_light:
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
                if self.current_segment == 0 and self.traffic_light:
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

            # Check if vehicle is on same path and heading same direction
            if hasattr(vehicle, 'path') and vehicle.path and self.path:
                # Check if they are on the same road segment
                if (vehicle.current_target_index == self.current_target_index and
                        vehicle.current_target == self.current_target):

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