"""
Module with pure implementations of traffic light control algorithms.
All functions only accept data and return new state.
"""

from typing import Dict, List, Tuple, Any
import numpy as np
from dataclasses import dataclass
from enum import Enum

class TrafficLightState(Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"

@dataclass
class TrafficLightData:
    """Traffic light data for algorithms"""
    id: int
    state: TrafficLightState
    position: Tuple[float, float]
    direction: str
    timer: int = 0
    green_duration: int = 30
    yellow_duration: int = 5
    red_duration: int = 35
    queue_length: int = 0
    neighbors: List[int] = None

    def __post_init__(self):
        if self.neighbors is None:
            self.neighbors = []

@dataclass
class SimulationContext:
    """Simulation context for algorithms"""
    current_step: int
    vehicles_data: List[Dict[str, Any]]
    traffic_lights_data: List[TrafficLightData]
    config: Dict[str, Any]

class StaticAlgorithm:
    """Static algorithm with fixed cycle times"""

    def __init__(self, config: Dict = None):
        self.config = config or {
            "green_duration": 30,
            "yellow_duration": 5,
            "red_duration": 35,
            "cycle_offset": 0
        }

    def calculate_state(self, light: TrafficLightData, context: SimulationContext) -> TrafficLightState:
        """Calculate traffic light state using static algorithm"""
        total_cycle = (self.config["green_duration"] +
                      self.config["yellow_duration"] +
                      self.config["red_duration"])

        adjusted_step = (context.current_step +
                        self.config.get("cycle_offset", 0) * light.id) % total_cycle

        if adjusted_step < self.config["green_duration"]:
            return TrafficLightState.GREEN
        elif adjusted_step < self.config["green_duration"] + self.config["yellow_duration"]:
            return TrafficLightState.YELLOW
        else:
            return TrafficLightState.RED

    def update_light(self, light: TrafficLightData, context: SimulationContext) -> TrafficLightData:
        """Update traffic light data"""
        new_state = self.calculate_state(light, context)

        return TrafficLightData(
            id=light.id,
            state=new_state,
            position=light.position,
            direction=light.direction,
            timer=light.timer + 1,
            green_duration=light.green_duration,
            yellow_duration=light.yellow_duration,
            red_duration=light.red_duration,
            queue_length=light.queue_length,
            neighbors=light.neighbors
        )

class AdaptiveAlgorithm:
    """Adaptive algorithm based on queue length"""

    def __init__(self, config: Dict = None):
        self.config = config or {
            "base_green_time": 20,
            "max_green_time": 60,
            "min_green_time": 10,
            "queue_threshold_high": 15,
            "queue_threshold_medium": 8,
            "queue_increase_factor": 1.5,
            "queue_decrease_factor": 0.7,
            "adaptation_rate": 0.1
        }

    def _calculate_green_time(self, queue_length: int, current_green: int) -> int:
        """Calculate green time based on queue"""
        if queue_length > self.config["queue_threshold_high"]:
            target_time = min(
                self.config["max_green_time"],
                current_green * self.config["queue_increase_factor"]
            )
        elif queue_length > self.config["queue_threshold_medium"]:
            target_time = min(
                self.config["max_green_time"],
                current_green * 1.2
            )
        else:
            target_time = max(
                self.config["min_green_time"],
                current_green * self.config["queue_decrease_factor"]
            )

        new_time = int(current_green +
                      (target_time - current_green) * self.config["adaptation_rate"])

        return new_time

    def calculate_state(self, light: TrafficLightData, context: SimulationContext) -> TrafficLightState:
        """Calculate traffic light state using adaptive algorithm"""
        new_green_time = self._calculate_green_time(
            light.queue_length,
            light.green_duration
        )

        total_cycle = new_green_time + light.yellow_duration + light.red_duration

        step_in_cycle = context.current_step % total_cycle

        if step_in_cycle < new_green_time:
            return TrafficLightState.GREEN
        elif step_in_cycle < new_green_time + light.yellow_duration:
            return TrafficLightState.YELLOW
        else:
            return TrafficLightState.RED

    def update_light(self, light: TrafficLightData, context: SimulationContext) -> TrafficLightData:
        """Update traffic light data with adaptation"""
        new_state = self.calculate_state(light, context)

        new_green_time = self._calculate_green_time(
            light.queue_length,
            light.green_duration
        )

        return TrafficLightData(
            id=light.id,
            state=new_state,
            position=light.position,
            direction=light.direction,
            timer=light.timer + 1,
            green_duration=new_green_time,
            yellow_duration=light.yellow_duration,
            red_duration=light.red_duration,
            queue_length=light.queue_length,
            neighbors=light.neighbors
        )

class CoordinatedAlgorithm:
    """Coordinated algorithm for traffic light networks"""

    def __init__(self, config: Dict = None):
        self.config = config or {
            "base_green_time": 25,
            "coordination_radius": 50.0,
            "green_wave_speed": 10.0,
            "offset_calculation": "distance_based",
            "min_offset": 5,
            "max_offset": 30,
            "sync_tolerance": 3
        }

    def _calculate_offset(self, light: TrafficLightData, neighbors: List[TrafficLightData]) -> int:
        """Calculate phase offset for coordination"""
        if not neighbors:
            return 0

        if self.config["offset_calculation"] == "distance_based":
            distances = []
            for neighbor in neighbors:
                dist = np.sqrt(
                    (light.position[0] - neighbor.position[0])**2 +
                    (light.position[1] - neighbor.position[1])**2
                )
                if dist <= self.config["coordination_radius"]:
                    travel_time = dist / self.config["green_wave_speed"]
                    distances.append(travel_time)

            if distances:
                avg_travel_time = np.mean(distances)
                offset = int(avg_travel_time) % light.green_duration
                return min(max(offset, self.config["min_offset"]), self.config["max_offset"])

        return 0

    def _should_extend_green(self, light: TrafficLightData, neighbors: List[TrafficLightData]) -> bool:
        """Determine if green signal should be extended"""
        approaching_vehicles = 0
        for neighbor in neighbors:
            if neighbor.state == TrafficLightState.RED and neighbor.timer > neighbor.red_duration - 5:
                if light.queue_length > 3:
                    approaching_vehicles += 1

        return approaching_vehicles > 0

    def calculate_state(self, light: TrafficLightData, context: SimulationContext) -> TrafficLightState:
        """Calculate traffic light state with coordination"""
        neighbors = [
            tl for tl in context.traffic_lights_data
            if tl.id in light.neighbors
        ]

        offset = self._calculate_offset(light, neighbors)

        adaptive_algo = AdaptiveAlgorithm()
        base_state = adaptive_algo.calculate_state(light, context)

        if base_state == TrafficLightState.GREEN:
            if self._should_extend_green(light, neighbors):
                adjusted_step = (context.current_step + offset) % (light.green_duration + 5)
                if adjusted_step < light.green_duration:
                    return TrafficLightState.GREEN
                else:
                    return TrafficLightState.YELLOW
            else:
                adjusted_step = (context.current_step + offset) % light.green_duration
                if adjusted_step < light.green_duration - 5:
                    return TrafficLightState.GREEN
                else:
                    return TrafficLightState.YELLOW
        else:
            return base_state

    def update_light(self, light: TrafficLightData, context: SimulationContext) -> TrafficLightData:
        """Update traffic light data with coordination"""
        new_state = self.calculate_state(light, context)

        neighbors = [
            tl for tl in context.traffic_lights_data
            if tl.id in light.neighbors
        ]

        adaptive_algo = AdaptiveAlgorithm()
        new_green_time = adaptive_algo._calculate_green_time(
            light.queue_length,
            light.green_duration
        )

        if self._should_extend_green(light, neighbors):
            new_green_time = min(new_green_time + 5, 60)

        return TrafficLightData(
            id=light.id,
            state=new_state,
            position=light.position,
            direction=light.direction,
            timer=light.timer + 1,
            green_duration=new_green_time,
            yellow_duration=light.yellow_duration,
            red_duration=light.red_duration,
            queue_length=light.queue_length,
            neighbors=light.neighbors
        )

class AlgorithmFactory:
    """Factory for creating algorithms"""

    @staticmethod
    def create_algorithm(algorithm_type: str, config: Dict = None) -> Any:
        """Create algorithm by type"""
        algorithms = {
            "static": StaticAlgorithm,
            "adaptive": AdaptiveAlgorithm,
            "coordinated": CoordinatedAlgorithm
        }

        if algorithm_type not in algorithms:
            raise ValueError(f"Unknown algorithm type: {algorithm_type}")

        return algorithms[algorithm_type](config)

    @staticmethod
    def get_algorithm_info() -> List[Dict]:
        """Get information about available algorithms"""
        return [
            {
                "id": "static",
                "name": "Static Algorithm",
                "description": "Fixed time cycles without adaptation",
                "parameters": [
                    {"name": "green_duration", "type": "int", "default": 30, "min": 10, "max": 60},
                    {"name": "yellow_duration", "type": "int", "default": 5, "min": 3, "max": 10},
                    {"name": "red_duration", "type": "int", "default": 35, "min": 20, "max": 70}
                ]
            },
            {
                "id": "adaptive",
                "name": "Adaptive Algorithm",
                "description": "Adjusts green time based on queue length",
                "parameters": [
                    {"name": "base_green_time", "type": "int", "default": 20, "min": 10, "max": 40},
                    {"name": "max_green_time", "type": "int", "default": 60, "min": 30, "max": 90},
                    {"name": "queue_threshold_high", "type": "int", "default": 15, "min": 5, "max": 30},
                    {"name": "queue_threshold_medium", "type": "int", "default": 8, "min": 3, "max": 20}
                ]
            },
            {
                "id": "coordinated",
                "name": "Coordinated Algorithm",
                "description": "Coordinates multiple traffic lights for green waves",
                "parameters": [
                    {"name": "coordination_radius", "type": "float", "default": 50.0, "min": 10.0, "max": 200.0},
                    {"name": "green_wave_speed", "type": "float", "default": 10.0, "min": 5.0, "max": 20.0},
                    {"name": "min_offset", "type": "int", "default": 5, "min": 0, "max": 20},
                    {"name": "max_offset", "type": "int", "default": 30, "min": 10, "max": 60}
                ]
            }
        ]