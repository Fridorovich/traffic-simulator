import mesa
import numpy as np
from typing import Dict, List, Tuple, Optional
import random
from .agents import VehicleAgent, TrafficLightAgent, TrafficLightState


class TrafficModel(mesa.Model):
    """Main traffic simulation model"""

    def __init__(self, config: Dict = None):
        super().__init__()

        self.default_config = {
            "grid_width": 50,
            "grid_height": 50,
            "num_vehicles": 20,
            "algorithm": "static",
            "algorithm_config": {},
            "spawn_rate": 0.1,
            "simulation_speed": 1,
            "road_config": "crossroad"
        }

        self.config = {**self.default_config, **(config or {})}

        self.grid = mesa.space.ContinuousSpace(
            self.config["grid_width"],
            self.config["grid_height"],
            torus=False
        )
        self.schedule = mesa.time.RandomActivation(self)

        self.vehicles: List[VehicleAgent] = []
        self.traffic_lights: List[TrafficLightAgent] = []

        self.completed_vehicles = 0
        self.spawned_vehicles = 0
        self.historical_metrics = {
            "waiting_time_history": [],
            "delay_history": [],
            "throughput_history": [],
            "speed_history": [],
            "vehicle_count_history": []
        }

        self._generate_road_network()

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Total_Vehicles": lambda m: len(m.vehicles),
                "Avg_Waiting_Time": lambda m: m._calculate_avg_waiting_time(),
                "Total_Delay": lambda m: m._calculate_total_delay(),
                "Throughput": lambda m: m._calculate_throughput(),
                "Avg_Speed": lambda m: m._calculate_avg_speed(),
                "Algorithm": lambda m: m.config["algorithm"]
            },
            agent_reporters={
                "Type": lambda a: type(a).__name__,
                "Position": lambda a: a.position if hasattr(a, 'position') else None,
                "Speed": lambda a: a.speed if hasattr(a, 'speed') else 0,
                "Waiting_Time": lambda a: a.waiting_time if hasattr(a, 'waiting_time') else 0,
                "State": lambda a: a.state.value if hasattr(a, 'state') else None,
                "Queue_Length": lambda a: a.get_queue_length() if hasattr(a, 'get_queue_length') else 0,
            }
        )

        self.steps = 0

    def _generate_road_network(self):
        """Generate road network (intersection)"""
        center_x = self.config["grid_width"] // 2
        center_y = self.config["grid_height"] // 2

        light_positions = [
            (center_x - 10, center_y, "horizontal"),
            (center_x + 10, center_y, "horizontal"),
            (center_x, center_y - 10, "vertical"),
            (center_x, center_y + 10, "vertical")
        ]

        algorithm_type = self.config["algorithm"]

        for i, (x, y, direction) in enumerate(light_positions):
            light = TrafficLightAgent(
                unique_id=1000 + i,
                model=self,
                position=(x, y),
                direction=direction,
                algorithm_type=algorithm_type
            )
            self.traffic_lights.append(light)
            self.schedule.add(light)
            self.grid.place_agent(light, (x, y))

        for i in range(self.config["num_vehicles"]):
            self._spawn_vehicle(i)

    def _spawn_vehicle(self, vehicle_id: int):
        """Create new vehicle"""
        spawn_points = [
            (0, self.config["grid_height"] // 2),
            (self.config["grid_width"] - 1, self.config["grid_height"] // 2),
            (self.config["grid_width"] // 2, 0),
            (self.config["grid_width"] // 2, self.config["grid_height"] - 1)
        ]

        spawn_point = random.choice(spawn_points)

        vehicle = VehicleAgent(
            unique_id=vehicle_id,
            model=self,
            spawn_point=spawn_point
        )

        self.vehicles.append(vehicle)
        self.schedule.add(vehicle)
        self.grid.place_agent(vehicle, spawn_point)
        self.spawned_vehicles += 1

    def is_position_occupied(self, position: Tuple[float, float], exclude_id: int = None) -> bool:
        """Check if position is occupied by another vehicle"""
        neighbors = self.grid.get_neighbors(position, radius=1.5, include_center=True)

        for agent in neighbors:
            if isinstance(agent, VehicleAgent) and agent.unique_id != exclude_id:
                distance = np.sqrt((agent.position[0] - position[0]) ** 2 +
                                   (agent.position[1] - position[1]) ** 2)
                if distance < 1.0:
                    return True

        return False

    def vehicle_completed(self, vehicle: VehicleAgent):
        """Handle vehicle route completion"""
        self.vehicles.remove(vehicle)
        self.schedule.remove(vehicle)
        self.grid.remove_agent(vehicle)
        self.completed_vehicles += 1

        if random.random() < self.config["spawn_rate"]:
            new_id = max([v.unique_id for v in self.vehicles], default=0) + 1
            self._spawn_vehicle(new_id)

    def _calculate_avg_waiting_time(self) -> float:
        """Calculate average waiting time"""
        if not self.vehicles:
            return 0.0
        total_waiting = sum(vehicle.waiting_time for vehicle in self.vehicles)
        return total_waiting / len(self.vehicles)

    def _calculate_total_delay(self) -> float:
        """Calculate total delay time"""
        if not self.vehicles:
            return 0.0

        total_delay = 0
        for vehicle in self.vehicles:
            ideal_time = len(vehicle.route) * 10
            actual_time = vehicle.total_travel_time
            delay = max(0, actual_time - ideal_time)
            total_delay += delay

        return total_delay

    def _calculate_throughput(self) -> int:
        """Calculate throughput (vehicles per step)"""
        return self.completed_vehicles

    def _calculate_avg_speed(self) -> float:
        """Calculate average speed"""
        if not self.vehicles:
            return 0.0
        total_speed = sum(vehicle.speed for vehicle in self.vehicles)
        return total_speed / len(self.vehicles)

    def step(self):
        """Main simulation step"""
        self.schedule.step()

        self.datacollector.collect(self)

        self._update_historical_metrics()

        self.steps += 1

    def _update_historical_metrics(self):
        """Update historical metrics"""
        self.historical_metrics["waiting_time_history"].append(
            self._calculate_avg_waiting_time()
        )
        self.historical_metrics["delay_history"].append(
            self._calculate_total_delay()
        )
        self.historical_metrics["throughput_history"].append(
            self._calculate_throughput()
        )
        self.historical_metrics["speed_history"].append(
            self._calculate_avg_speed()
        )
        self.historical_metrics["vehicle_count_history"].append(
            len(self.vehicles)
        )

        max_history = 100
        for key in self.historical_metrics:
            if len(self.historical_metrics[key]) > max_history:
                self.historical_metrics[key] = self.historical_metrics[key][-max_history:]

    def get_simulation_state(self) -> Dict:
        """Get current simulation state for API"""
        return {
            "simulation_id": f"sim_{id(self)}",
            "steps": self.steps,
            "vehicles": [
                {
                    "id": v.unique_id,
                    "x": float(v.position[0]),
                    "y": float(v.position[1]),
                    "color": v.color,
                    "speed": float(v.speed),
                    "waiting_time": v.waiting_time,
                    "current_segment": v.current_segment
                }
                for v in self.vehicles
            ],
            "traffic_lights": [
                tl.get_state_dict() for tl in self.traffic_lights
            ],
            "metrics": {
                "total_vehicles": len(self.vehicles),
                "avg_waiting_time": self._calculate_avg_waiting_time(),
                "total_delay": self._calculate_total_delay(),
                "throughput": self._calculate_throughput(),
                "avg_speed": self._calculate_avg_speed(),
                "completed_vehicles": self.completed_vehicles,
                "spawned_vehicles": self.spawned_vehicles,
                "current_step": self.steps
            },
            "historical_metrics": self.historical_metrics,
            "config": self.config,
            "timestamp": self.steps
        }

    def change_algorithm(self, new_algorithm: str, config: Dict = None):
        """Change control algorithm for all traffic lights"""
        self.config["algorithm"] = new_algorithm

        for light in self.traffic_lights:
            light.algorithm_type = new_algorithm

    def get_traffic_light_for_vehicle(self, vehicle: VehicleAgent) -> Optional[TrafficLightAgent]:
        """Get traffic light controlling this vehicle's movement"""
        if not vehicle.route or vehicle.current_segment >= len(vehicle.route):
            return None

        target_pos = vehicle.route[vehicle.current_segment]

        dx = target_pos[0] - vehicle.position[0]
        dy = target_pos[1] - vehicle.position[1]

        closest_light = None
        min_distance = float('inf')

        for light in self.traffic_lights:
            if abs(dx) > abs(dy):
                if light.direction == "horizontal":
                    if abs(vehicle.position[1] - light.position[1]) < 3:
                        distance = abs(vehicle.position[0] - light.position[0])
                        if distance < min_distance:
                            min_distance = distance
                            closest_light = light
            else:
                if light.direction == "vertical":
                    if abs(vehicle.position[0] - light.position[0]) < 3:
                        distance = abs(vehicle.position[1] - light.position[1])
                        if distance < min_distance:
                            min_distance = distance
                            closest_light = light

        return closest_light