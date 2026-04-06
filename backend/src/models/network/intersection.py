from typing import List, Dict, Optional, Tuple
import mesa
import numpy as np
from ..agents import TrafficLightAgent, TrafficLightState, LaneDirection


class IntersectionNode:
    """Represents a single intersection in the road network"""

    def __init__(self, intersection_id: int, x: float, y: float,
                 road_type: str = "crossroad"):
        self.id = intersection_id
        self.x = x
        self.y = y
        self.road_type = road_type
        self.traffic_lights: List[TrafficLightAgent] = []
        self.connected_roads: Dict[str, List['RoadSegment']] = {
            'RIGHT': [],
            'LEFT': [],
            'UP': [],
            'DOWN': []
        }

    def create_traffic_lights(self, model, algorithm_type: str):
        """Create traffic lights for this intersection"""
        lane_offset = 2.0

        if self.road_type == "crossroad":
            light_positions = [
                (self.x - 8, self.y, "horizontal", "left"),
                (self.x + 8, self.y, "horizontal", "right"),
                (self.x, self.y - 8, "vertical", "top"),
                (self.x, self.y + 8, "vertical", "bottom"),
            ]
        else:
            # T-intersection
            light_positions = [
                (self.x - 8, self.y, "horizontal", "left"),
                (self.x + 8, self.y, "horizontal", "right"),
                (self.x, self.y + 8, "vertical", "bottom"),
            ]

        for i, (x, y, direction, side) in enumerate(light_positions):
            light = TrafficLightAgent(
                unique_id=10000 + self.id * 10 + i,
                model=model,
                position=(x, y),
                direction=direction,
                algorithm_type=algorithm_type,
                intersection_type=self.road_type,
                side=side
            )
            self.traffic_lights.append(light)

    def get_traffic_light_for_direction(self, direction: str) -> Optional[TrafficLightAgent]:
        """Get traffic light for vehicles coming from specific direction"""
        for light in self.traffic_lights:
            if direction == "RIGHT" and light.side == "left":
                return light
            if direction == "LEFT" and light.side == "right":
                return light
            if direction == "DOWN" and light.side == "top":
                return light
            if direction == "UP" and light.side == "bottom":
                return light
        return None

    def get_state_dict(self) -> Dict:
        """Get state for API"""
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "road_type": self.road_type,
            "traffic_lights": [light.get_state_dict() for light in self.traffic_lights]
        }


class RoadSegment:
    """Represents a road between two intersections"""

    def __init__(self, from_intersection: IntersectionNode,
                 to_intersection: IntersectionNode, length: float, lanes: int = 2):
        self.from_node = from_intersection
        self.to_node = to_intersection
        self.length = length
        self.lanes = lanes

        # Determine direction
        if abs(to_intersection.x - from_intersection.x) > 0.1:
            if to_intersection.x > from_intersection.x:
                self.direction = "RIGHT"
            else:
                self.direction = "LEFT"
        else:
            if to_intersection.y > from_intersection.y:
                self.direction = "DOWN"
            else:
                self.direction = "UP"

        # Vehicles currently on this segment
        self.vehicles_on_segment: List = []

    def get_start_point(self) -> Tuple[float, float]:
        """Get start point of the road segment"""
        return (self.from_node.x, self.from_node.y)

    def get_end_point(self) -> Tuple[float, float]:
        """Get end point of the road segment"""
        return (self.to_node.x, self.to_node.y)

    def get_traffic_light_for_entry(self) -> Optional[TrafficLightAgent]:
        """Get traffic light at the end of this segment"""
        return self.to_node.get_traffic_light_for_direction(self.direction)