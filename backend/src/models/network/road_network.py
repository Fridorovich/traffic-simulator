from typing import List, Dict, Optional, Tuple
import random
from .intersection import IntersectionNode, RoadSegment
from .network_vehicle import NetworkVehicleAgent
from .path_finder import PathFinder
from .network_config import NetworkConfig
from ..agents import VehicleAgent, LaneDirection


class RoadNetwork:
    """Complete road network with multiple intersections"""

    def __init__(self, config: NetworkConfig, model):
        self.model = model
        self.intersections: Dict[int, IntersectionNode] = {}
        self.roads: List[RoadSegment] = []
        self.path_finder = PathFinder(self)
        self.config = config

        # Build network from config
        self._build_network()

    def _build_network(self):
        """Build network from configuration"""
        # Create intersections
        for intersection_config in self.config.intersections:
            node = IntersectionNode(
                intersection_id=intersection_config.id,
                x=intersection_config.x,
                y=intersection_config.y,
                road_type=intersection_config.road_type
            )
            self.intersections[node.id] = node

        # Create roads
        for road_config in self.config.roads:
            from_node = self.intersections[road_config.from_intersection]
            to_node = self.intersections[road_config.to_intersection]
            road = RoadSegment(from_node, to_node, road_config.length, road_config.lanes)
            self.roads.append(road)

            # Register road in from_node
            from_node.connected_roads[road.direction].append(road)

    def create_traffic_lights(self, model, algorithm_type: str):
        """Create all traffic lights in the network"""
        for node in self.intersections.values():
            node.create_traffic_lights(model, algorithm_type)

    def get_traffic_lights(self):
        """Get all traffic lights"""
        lights = []
        for node in self.intersections.values():
            lights.extend(node.traffic_lights)
        return lights

    def get_intersection(self, node_id: int) -> Optional[IntersectionNode]:
        """Get intersection by ID"""
        return self.intersections.get(node_id)

    def get_neighbors(self, node_id: int) -> List[int]:
        """Get neighboring intersection IDs"""
        neighbors = []
        node = self.intersections.get(node_id)
        if node:
            for roads in node.connected_roads.values():
                for road in roads:
                    neighbors.append(road.to_node.id)
        return neighbors

    def get_random_spawn_point(self) -> Optional[Tuple[float, float, str]]:
        """Get random spawn point"""
        if not self.config.spawn_points:
            return None
        return random.choice(self.config.spawn_points)

    def get_random_destination(self) -> Optional[Tuple[float, float]]:
        """Get random destination point"""
        if not self.config.despawn_points:
            return None
        return random.choice(self.config.despawn_points)

    def get_road_between(self, from_node_id: int, to_node_id: int) -> Optional[RoadSegment]:
        """Get road segment between two intersections"""
        for road in self.roads:
            if road.from_node.id == from_node_id and road.to_node.id == to_node_id:
                return road
        return None

    def spawn_vehicle_on_network(self, vehicle_id: int) -> bool:
        """Spawn a vehicle on the road network"""
        if len(self.model.vehicles) > 100:
            return False

        if not self.config.spawn_points:
            return False

        spawn_info = random.choice(self.config.spawn_points)
        x, y, direction_str = spawn_info

        # Convert direction string to LaneDirection
        direction_map = {
            "RIGHT": LaneDirection.RIGHT,
            "LEFT": LaneDirection.LEFT,
            "UP": LaneDirection.UP,
            "DOWN": LaneDirection.DOWN
        }

        direction = direction_map[direction_str]
        lane = random.randint(0, 1)
        lane_offset = 2.0

        # Adjust spawn position based on lane
        if direction_str in ["RIGHT", "LEFT"]:
            y = y + (lane_offset if lane == 1 else -lane_offset)
        else:
            x = x + (lane_offset if lane == 1 else -lane_offset)

        # Find random destination point
        if self.config.despawn_points:
            dest_x, dest_y = random.choice(self.config.despawn_points)
        else:
            dest_x, dest_y = x + 50, y + 50

        # Create vehicle
        vehicle = NetworkVehicleAgent(
            unique_id=vehicle_id,
            model=self.model,
            spawn_point=(x, y),
            lane=lane,
            direction=direction,
            network=self,
            destination=(dest_x, dest_y)
        )

        self.model.vehicles.append(vehicle)
        self.model.schedule.add(vehicle)
        self.model.grid.place_agent(vehicle, (x, y))
        self.model.spawned_vehicles += 1
        return True

    def get_state_dict(self) -> Dict:
        """Get network state for API - без дублирования"""
        # Используем словарь для уникальных пересечений
        unique_intersections = {}
        for node in self.intersections.values():
            key = f"{node.x},{node.y}"
            if key not in unique_intersections:
                unique_intersections[key] = {
                    "id": node.id,
                    "x": node.x,
                    "y": node.y,
                    "road_type": node.road_type,
                    "traffic_lights_count": len(node.traffic_lights)
                }

        return {
            "intersections": list(unique_intersections.values()),
            "roads": [
                {
                    "from": road.from_node.id,
                    "to": road.to_node.id,
                    "direction": road.direction,
                    "length": float(road.length)
                }
                for road in self.roads
            ]
        }