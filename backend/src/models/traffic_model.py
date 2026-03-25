import mesa
import numpy as np
from typing import Dict, List, Tuple, Optional
import random
from .agents import VehicleAgent, TrafficLightAgent, TrafficLightState, LaneDirection


class TrafficModel(mesa.Model):
    """Main traffic simulation model with two-lane system"""

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
            "vehicle_count_history": [],
            "stops_history": [],
            "co2_history": []
        }

        self._generate_road_network()

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Total_Vehicles": lambda m: len(m.vehicles),
                "Avg_Waiting_Time": lambda m: m._calculate_avg_waiting_time(),
                "Total_Delay": lambda m: m._calculate_total_delay(),
                "Throughput": lambda m: m._calculate_throughput(),
                "Avg_Speed": lambda m: m._calculate_avg_speed(),
                "Algorithm": lambda m: m.config["algorithm"],
                "Total_Stops": lambda m: m._calculate_total_stops(),
                "Total_CO2_g": lambda m: m._calculate_total_co2_emissions(),
            },
            agent_reporters={
                "Type": lambda a: type(a).__name__,
                "Position_X": lambda a: a.position[0] if hasattr(a, 'position') else 0,
                "Position_Y": lambda a: a.position[1] if hasattr(a, 'position') else 0,
                "Speed": lambda a: a.speed if hasattr(a, 'speed') else 0,
                "Waiting_Time": lambda a: a.waiting_time if hasattr(a, 'waiting_time') else 0,
                "Stops": lambda a: a.number_of_stops if hasattr(a, 'number_of_stops') else 0,
                "CO2_g": lambda a: a.total_co2_emission if hasattr(a, 'total_co2_emission') else 0,
                "State": lambda a: a.state.value if hasattr(a, 'state') else None,
                "Queue_Length": lambda a: a.get_queue_length() if hasattr(a, 'get_queue_length') else 0,
                "Direction": lambda a: a.direction_str if hasattr(a, 'direction_str') else None,
                "Lane": lambda a: a.lane if hasattr(a, 'lane') else 0,
            }
        )

        self.steps = 0

    def _generate_road_network(self):
        """Generate road network with traffic lights at intersection"""
        center_x = self.config["grid_width"] // 2
        center_y = self.config["grid_height"] // 2

        light_positions = [
            (center_x - 5, center_y, "horizontal"),
            (center_x + 5, center_y, "horizontal"),
            (center_x, center_y - 5, "vertical"),
            (center_x, center_y + 5, "vertical"),
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

    def _spawn_vehicle(self, vehicle_id: int) -> bool:
        """Create new vehicle with lane-based spawning"""
        if len(self.vehicles) > 100:
            return False

        grid_width = self.config["grid_width"]
        grid_height = self.config["grid_height"]
        center_x = grid_width // 2
        center_y = grid_height // 2
        lane_offset = 2.0

        spawn_configs = [
            (0, center_y - lane_offset, LaneDirection.RIGHT, 0),
            (grid_width - 1, center_y + lane_offset, LaneDirection.LEFT, 1),
            (center_x + lane_offset, 0, LaneDirection.DOWN, 1),
            (center_x - lane_offset, grid_height - 1, LaneDirection.UP, 0),
        ]

        random.shuffle(spawn_configs)

        for x, y, direction, lane in spawn_configs:
            point_occupied = False
            for vehicle in self.vehicles:
                if abs(vehicle.position[0] - x) < 2 and abs(vehicle.position[1] - y) < 2:
                    point_occupied = True
                    break

            if not point_occupied:
                vehicle = VehicleAgent(
                    unique_id=vehicle_id,
                    model=self,
                    spawn_point=(x, y),
                    lane=lane,
                    direction=direction
                )
                self.vehicles.append(vehicle)
                self.schedule.add(vehicle)
                self.grid.place_agent(vehicle, (x, y))
                self.spawned_vehicles += 1
                return True

        return False

    def _get_next_vehicle_id(self) -> int:
        """Get next available vehicle ID"""
        if not self.vehicles:
            return 0
        return max([v.unique_id for v in self.vehicles]) + 1

    def is_position_occupied(self, position: Tuple[float, float], exclude_id: int = None) -> bool:
        """Check if position is occupied by another vehicle"""
        for agent in self.vehicles:
            if agent.unique_id == exclude_id:
                continue
            distance = np.sqrt((agent.position[0] - position[0]) ** 2 +
                               (agent.position[1] - position[1]) ** 2)
            if distance < 1.0:
                return True
        return False

    def vehicle_completed(self, vehicle: VehicleAgent):
        """Handle vehicle route completion"""
        if vehicle in self.vehicles:
            self.vehicles.remove(vehicle)
        self.schedule.remove(vehicle)
        self.grid.remove_agent(vehicle)
        self.completed_vehicles += 1

        if random.random() < self.config["spawn_rate"]:
            new_id = self._get_next_vehicle_id()
            self._spawn_vehicle(new_id)

    def step(self):
        """Main simulation step"""
        self.schedule.step()

        if len(self.vehicles) < self.config["num_vehicles"] * 1.5:
            if random.random() < self.config["spawn_rate"] / 5:
                self._spawn_vehicle(self._get_next_vehicle_id())

        self.datacollector.collect(self)
        self._update_historical_metrics()
        self.steps += 1

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
            ideal_time = 50
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

    def _calculate_total_stops(self) -> int:
        """Calculate total number of stops across all vehicles"""
        if not self.vehicles:
            return 0
        return int(sum(vehicle.number_of_stops for vehicle in self.vehicles))

    def _calculate_average_stops_per_vehicle(self) -> float:
        """Calculate average stops per vehicle"""
        if not self.vehicles:
            return 0.0
        total_stops = self._calculate_total_stops()
        return float(total_stops) / len(self.vehicles)

    def _calculate_total_co2_emissions(self) -> float:
        """Calculate total CO2 emissions in grams"""
        if not self.vehicles:
            return 0.0
        return float(sum(vehicle.total_co2_emission for vehicle in self.vehicles))

    def _calculate_average_co2_per_vehicle(self) -> float:
        """Calculate average CO2 emissions per vehicle in grams"""
        if not self.vehicles:
            return 0.0
        return self._calculate_total_co2_emissions() / len(self.vehicles)

    def _update_historical_metrics(self):
        """Update historical metrics including environmental data"""
        self.historical_metrics["waiting_time_history"].append(float(self._calculate_avg_waiting_time()))
        self.historical_metrics["delay_history"].append(float(self._calculate_total_delay()))
        self.historical_metrics["throughput_history"].append(int(self._calculate_throughput()))
        self.historical_metrics["speed_history"].append(float(self._calculate_avg_speed()))
        self.historical_metrics["vehicle_count_history"].append(int(len(self.vehicles)))
        self.historical_metrics["stops_history"].append(int(self._calculate_total_stops()))
        self.historical_metrics["co2_history"].append(float(self._calculate_total_co2_emissions()))

        max_history = 100
        for key in self.historical_metrics:
            if len(self.historical_metrics[key]) > max_history:
                self.historical_metrics[key] = self.historical_metrics[key][-max_history:]

    def get_simulation_state(self) -> Dict:
        """Get current simulation state for API with proper JSON serialization"""
        state = {
            "simulation_id": f"sim_{id(self)}",
            "steps": int(self.steps),
            "vehicles": [
                {
                    "id": int(v.unique_id),
                    "x": float(v.position[0]),
                    "y": float(v.position[1]),
                    "color": str(v.color),
                    "speed": float(v.speed),
                    "waiting_time": int(v.waiting_time),
                    "stopped": bool(v.stopped),
                    "stops": int(v.number_of_stops),
                    "co2_g": float(round(v.total_co2_emission, 2)),
                    "direction": str(v.direction_str),
                    "lane": int(v.lane)
                }
                for v in self.vehicles
            ],
            "traffic_lights": [tl.get_state_dict() for tl in self.traffic_lights],
            "metrics": {
                "total_vehicles": int(len(self.vehicles)),
                "avg_waiting_time": float(self._calculate_avg_waiting_time()),
                "total_delay": float(self._calculate_total_delay()),
                "throughput": int(self._calculate_throughput()),
                "avg_speed": float(self._calculate_avg_speed()),
                "completed_vehicles": int(self.completed_vehicles),
                "spawned_vehicles": int(self.spawned_vehicles),
                "current_step": int(self.steps),
                "total_stops": int(self._calculate_total_stops()),
                "avg_stops_per_vehicle": float(round(self._calculate_average_stops_per_vehicle(), 2)),
                "total_co2_g": float(round(self._calculate_total_co2_emissions(), 2)),
                "total_co2_kg": float(round(self._calculate_total_co2_emissions() / 1000, 3)),
                "avg_co2_per_vehicle_g": float(round(self._calculate_average_co2_per_vehicle(), 2)),
            },
            "historical_metrics": {
                "waiting_time_history": [float(x) for x in self.historical_metrics.get("waiting_time_history", [])],
                "delay_history": [float(x) for x in self.historical_metrics.get("delay_history", [])],
                "throughput_history": [int(x) for x in self.historical_metrics.get("throughput_history", [])],
                "speed_history": [float(x) for x in self.historical_metrics.get("speed_history", [])],
                "vehicle_count_history": [int(x) for x in self.historical_metrics.get("vehicle_count_history", [])],
                "stops_history": [int(x) for x in self.historical_metrics.get("stops_history", [])],
                "co2_history": [float(x) for x in self.historical_metrics.get("co2_history", [])],
            },
            "config": self.config,
            "timestamp": int(self.steps)
        }
        return state

    def change_algorithm(self, new_algorithm: str, config: Dict = None):
        """Change control algorithm for all traffic lights"""
        self.config["algorithm"] = new_algorithm
        if config:
            self.config["algorithm_config"] = config

        for light in self.traffic_lights:
            light.algorithm_type = new_algorithm
            light.timer = 0
            if new_algorithm == "static":
                light.green_duration = config.get("green_duration", 30) if config else 30
                light.yellow_duration = config.get("yellow_duration", 5) if config else 5
                light.red_duration = config.get("red_duration", 35) if config else 35
            elif new_algorithm == "adaptive":
                light.green_duration = config.get("base_green_time", 20) if config else 20
            elif new_algorithm == "coordinated":
                light.green_duration = config.get("base_green_time", 25) if config else 25

    def get_traffic_light_for_vehicle(self, vehicle: VehicleAgent) -> Optional[TrafficLightAgent]:
        """Get traffic light controlling this vehicle"""
        return vehicle.traffic_light