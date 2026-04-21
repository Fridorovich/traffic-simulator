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
    """Agent representing a vehicle with support for turns on T-intersection and crossroads"""

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
        self.passed_intersection = False   # флаг, что автомобиль уже проехал перекрёсток

        # Инициализация маршрута и поиск светофора
        self._init_path()
        self.traffic_light = self._find_first_traffic_light(model.traffic_lights)

    def _init_path(self):
        """Инициализация маршрута: start → intersection → (turn_point) → end"""
        grid_width = self.model.grid.width
        grid_height = self.model.grid.height
        center_x = grid_width // 2
        center_y = grid_height // 2
        lane_offset = 2.0

        road_config = self.model.config.get("road_config", "crossroad")
        self.turn_point = None   # промежуточная точка после поворота (если нужна)

        if road_config == "t_intersection":
            # --- Т-образный перекрёсток ---
            if self.direction == LaneDirection.RIGHT:
                # Движение слева направо – только прямо
                self.start_x = 0
                self.start_y = center_y - lane_offset
                self.intersection_x = center_x
                self.intersection_y = self.start_y
                self.end_x = grid_width - 1
                self.end_y = self.start_y
                self.turn_point = None

            elif self.direction == LaneDirection.LEFT:
                # Движение справа налево – только прямо
                self.start_x = grid_width - 1
                self.start_y = center_y + lane_offset
                self.intersection_x = center_x
                self.intersection_y = self.start_y
                self.end_x = 0
                self.end_y = self.start_y
                self.turn_point = None

            elif self.direction == LaneDirection.UP:
                # Движение снизу вверх – поворот налево или направо в зависимости от полосы
                self.start_y = grid_height - 1
                self.start_x = center_x + (lane_offset if self.lane == 1 else -lane_offset)
                self.intersection_x = self.start_x
                self.intersection_y = center_y

                if self.lane == 0:  # левая полоса -> поворот налево
                    self.end_x = 0
                    self.end_y = center_y + lane_offset
                    self.turn_point = (center_x - lane_offset, center_y + lane_offset)
                else:  # правая полоса -> поворот направо
                    self.end_x = grid_width - 1
                    self.end_y = center_y - lane_offset
                    self.turn_point = (center_x + lane_offset, center_y - lane_offset)

            else:  # DOWN – на Т-образном перекрёстке движения сверху вниз нет
                # Запасной вариант – поехать вниз до края (маловероятно)
                self.start_x = center_x + (lane_offset if self.lane == 1 else -lane_offset)
                self.start_y = 0
                self.intersection_x = self.start_x
                self.intersection_y = center_y
                self.end_x = self.start_x
                self.end_y = grid_height - 1
                self.turn_point = None

        else:
            # --- Обычный перекрёсток (crossroad) ---
            if self.direction == LaneDirection.RIGHT:
                self.start_x = 0
                self.start_y = center_y - lane_offset
                self.intersection_x = center_x
                self.intersection_y = self.start_y
                self.end_x = grid_width - 1
                self.end_y = self.start_y
                self.turn_point = None

            elif self.direction == LaneDirection.LEFT:
                self.start_x = grid_width - 1
                self.start_y = center_y + lane_offset
                self.intersection_x = center_x
                self.intersection_y = self.start_y
                self.end_x = 0
                self.end_y = self.start_y
                self.turn_point = None

            elif self.direction == LaneDirection.DOWN:
                self.start_y = 0
                self.start_x = center_x + lane_offset
                self.intersection_x = self.start_x
                self.intersection_y = center_y
                self.end_x = self.start_x
                self.end_y = grid_height - 1
                self.turn_point = None

            else:  # UP
                self.start_y = grid_height - 1
                self.start_x = center_x - lane_offset
                self.intersection_x = self.start_x
                self.intersection_y = center_y
                self.end_x = self.start_x
                self.end_y = 0
                self.turn_point = None

        self.position = [self.start_x, self.start_y]

        # Построение маршрута: start → intersection → (turn_point) → end
        self.route = [self.start]
        if self.intersection is not None:
            self.route.append(self.intersection)
        if self.turn_point:
            self.route.append(self.turn_point)
        self.route.append(self.end)

        self.current_segment = 0

    @property
    def start(self):
        return (self.start_x, self.start_y)

    @property
    def intersection(self):
        return (self.intersection_x, self.intersection_y)

    @property
    def end(self):
        return (self.end_x, self.end_y)

    def _find_first_traffic_light(self, traffic_lights):
        """Найти светофор на пути автомобиля (перед пересечением)"""
        closest_light = None
        min_distance = float('inf')
        road_config = self.model.config.get("road_config", "crossroad")

        # --- Специальная обработка для Т-образного перекрёстка, направление UP ---
        if road_config == "t_intersection" and self.direction == LaneDirection.UP:
            for light in traffic_lights:
                if light.direction != "vertical":
                    continue
                # Светофор для нижнего подхода имеет side="bottom"
                if getattr(light, 'side', None) == "bottom":
                    # Проверяем, что светофор находится между стартом и перекрёстком
                    if (light.position[1] < self.start_y and
                            light.position[1] > self.intersection_y):
                        dist = self.start_y - light.position[1]
                        if dist < min_distance:
                            min_distance = dist
                            closest_light = light
            return closest_light

        # --- Общая логика для остальных направлений и обычного перекрёстка ---
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
            else:  # Vertical movement (UP/DOWN)
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
                else:  # UP (для обычного перекрёстка)
                    if light.position[1] < self.start_y and light.position[1] > self.intersection_y:
                        dist = self.start_y - light.position[1]
                        if dist < min_distance:
                            min_distance = dist
                            closest_light = light

        return closest_light

    def _generate_color(self):
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
        return random.choice(colors)

    def _calculate_distance(self, pos1, pos2):
        return np.sqrt((pos2[0] - pos1[0]) ** 2 + (pos2[1] - pos1[1]) ** 2)

    def _get_distance_to_light(self):
        """Расстояние до светофора вдоль пути"""
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
        """Проверка, проехал ли автомобиль светофор (упрощённо – по координатам)"""
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
        """Поиск автомобиля впереди на том же маршрутном сегменте и полосе"""
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

    def move(self):
        """Основная логика движения с учётом светофоров и поворотов"""
        was_moving = self.speed > 0

        if not self.route or self.current_segment >= len(self.route):
            return

        target_pos = self.route[self.current_segment]

        # Определяем, приближается ли автомобиль к перекрёстку (для проверки светофора)
        center_x = self.model.grid.width // 2
        center_y = self.model.grid.height // 2
        dist_to_center = self._calculate_distance(self.position, (center_x, center_y))
        # Если ещё не проехали перекрёсток и расстояние до центра меньше 15 – приближаемся
        approaching_intersection = (not self.passed_intersection) and (dist_to_center < 15)

        # Влияние светофора
        traffic_light_speed = self.max_speed
        if approaching_intersection and self.traffic_light and not self._has_passed_light():
            dist_to_light = self._get_distance_to_light()
            if dist_to_light < 8:
                if self.traffic_light.state == TrafficLightState.RED:
                    self.waiting_at_light = True
                    if dist_to_light < 2.0:
                        traffic_light_speed = 0
                    elif dist_to_light < 8.0:
                        traffic_light_speed = self.max_speed * (dist_to_light / 8.0)
                elif self.traffic_light.state == TrafficLightState.YELLOW:
                    if dist_to_light < 4.0:
                        traffic_light_speed = 0
                else:  # GREEN
                    self.waiting_at_light = False
            else:
                self.waiting_at_light = False
        else:
            self.waiting_at_light = False

        if self.waiting_at_light:
            self.speed = 0
            self.stopped = True
            self.waiting_time += 1
            self.total_travel_time += 1
            return

        # Автомобиль впереди
        vehicle_ahead = self._get_vehicle_ahead()
        safe_speed = self._calculate_safe_speed(vehicle_ahead)

        desired_speed = min(safe_speed, traffic_light_speed, self.max_speed)

        # Плавное изменение скорости
        if desired_speed < self.speed:
            self.speed = max(desired_speed, self.speed - self.deceleration)
        elif desired_speed > self.speed:
            self.speed = min(desired_speed, self.speed + self.acceleration)

        if self.speed < 0.01:
            self.speed = 0.0

        # Достижение текущей точки маршрута
        distance_to_target = self._calculate_distance(self.position, target_pos)
        if distance_to_target < 2.0:
            self.current_segment += 1
            if self.current_segment >= len(self.route):
                # Завершение маршрута
                self.model.vehicle_completed(self)
                return
            target_pos = self.route[self.current_segment]

        # Фиксация проезда перекрёстка (центр сетки)
        if not self.passed_intersection and dist_to_center < 2.0:
            self.passed_intersection = True

        # Движение к цели
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

        # Обновление состояния (остановка, подсчёт времени ожидания)
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
                 direction: str, algorithm_type: str = "static",
                 intersection_type: str = "crossroad", side: str = None):
        super().__init__(unique_id, model)
        self.position = position
        self.direction = direction
        self.state = TrafficLightState.RED
        self.algorithm_type = algorithm_type
        self.side = side
        self.intersection_type = intersection_type
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

    def get_traffic_light_by_id(self, light_id):
        for light in self.traffic_lights:
            if light.unique_id == light_id:
                return light
        return None

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
        """Static algorithm with fixed cycle times"""
        total_cycle = self.green_duration + self.yellow_duration + self.red_duration

        if self.intersection_type == "t_intersection":
            # Для T-образного перекрестка
            cycle_time = (self.model.schedule.steps + 30) % total_cycle

            if self.side == "bottom":
                # Нижняя сторона: RED -> GREEN -> YELLOW
                offset = self.green_duration + self.yellow_duration
                adjusted_time = (cycle_time + offset) % total_cycle
                if adjusted_time < self.green_duration:
                    self.state = TrafficLightState.GREEN
                elif adjusted_time < self.green_duration + self.yellow_duration:
                    self.state = TrafficLightState.YELLOW
                else:
                    self.state = TrafficLightState.RED
            else:
                # Левая и правая стороны: GREEN -> YELLOW -> RED
                if cycle_time < self.green_duration:
                    self.state = TrafficLightState.GREEN
                elif cycle_time < self.green_duration + self.yellow_duration:
                    self.state = TrafficLightState.YELLOW
                else:
                    self.state = TrafficLightState.RED
        else:
            # Стандартный перекресток (без изменений)
            cycle_time = (self.model.schedule.steps + 30) % total_cycle

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
            "id": int(self.unique_id),
            "x": float(self.position[0]),
            "y": float(self.position[1]),
            "state": str(self.state.value),
            "queue_length": self.get_queue_length(),
            "direction": str(self.direction),
            "side": str(self.side) if self.side else None,
            "intersection_type": str(self.intersection_type),
            "green_duration": int(self.green_duration),
            "max_queue": int(self.max_queue_length),
            "total_passed": int(self.total_vehicles_passed)
        }