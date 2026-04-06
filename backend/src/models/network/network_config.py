from typing import List, Tuple, Dict
from dataclasses import dataclass
import json


@dataclass
class IntersectionConfig:
    """Configuration for a single intersection"""
    id: int
    x: float
    y: float
    road_type: str = "crossroad"  # crossroad, t_intersection


@dataclass
class RoadConfig:
    """Configuration for a road segment"""
    from_intersection: int
    to_intersection: int
    length: float
    lanes: int = 2


@dataclass
class NetworkConfig:
    """Complete road network configuration"""
    intersections: List[IntersectionConfig]
    roads: List[RoadConfig]
    spawn_points: List[Tuple[float, float, str]]  # x, y, direction
    despawn_points: List[Tuple[float, float]]  # x, y

    @classmethod
    def create_grid(cls, rows: int, cols: int, spacing: float,
                    grid_width: float, grid_height: float) -> 'NetworkConfig':
        """Create a grid network"""
        intersections = []
        roads = []
        spawn_points = []
        despawn_points = []

        # Вычисляем общую ширину и высоту сетки
        total_width = (cols - 1) * spacing
        total_height = (rows - 1) * spacing

        # Вычисляем начальную позицию для центрирования
        start_x = (grid_width - total_width) / 2
        start_y = (grid_height - total_height) / 2

        print(f"Grid creation: {rows}x{cols}, spacing={spacing}")
        print(f"  Total size: {total_width} x {total_height}")
        print(f"  Start position: ({start_x}, {start_y})")

        for r in range(rows):
            for c in range(cols):
                x = start_x + c * spacing
                y = start_y + r * spacing
                intersections.append(IntersectionConfig(
                    id=r * cols + c,
                    x=x,
                    y=y,
                    road_type="crossroad"
                ))
                print(f"  Intersection {r * cols + c}: ({x:.1f}, {y:.1f})")

        # Create roads between intersections
        for r in range(rows):
            for c in range(cols):
                current_id = r * cols + c
                current = intersections[current_id]

                # Connect to right neighbor
                if c < cols - 1:
                    right_id = r * cols + (c + 1)
                    right = intersections[right_id]
                    distance = abs(right.x - current.x)
                    if distance > 0:
                        roads.append(RoadConfig(
                            from_intersection=current_id,
                            to_intersection=right_id,
                            length=distance
                        ))
                        roads.append(RoadConfig(
                            from_intersection=right_id,
                            to_intersection=current_id,
                            length=distance
                        ))

                # Connect to bottom neighbor
                if r < rows - 1:
                    bottom_id = (r + 1) * cols + c
                    bottom = intersections[bottom_id]
                    distance = abs(bottom.y - current.y)
                    if distance > 0:
                        roads.append(RoadConfig(
                            from_intersection=current_id,
                            to_intersection=bottom_id,
                            length=distance
                        ))
                        roads.append(RoadConfig(
                            from_intersection=bottom_id,
                            to_intersection=current_id,
                            length=distance
                        ))

        # Add spawn points on all four sides
        # Top spawn points (from top row intersections going down)
        for c in range(cols):
            inter = intersections[c]  # first row
            x = inter.x
            y = inter.y - spacing / 2
            if y > 5:
                spawn_points.append((x, y, "DOWN"))
                despawn_points.append((x, y - 10))

        # Bottom spawn points (from bottom row intersections going up)
        for c in range(cols):
            inter = intersections[(rows - 1) * cols + c]  # last row
            x = inter.x
            y = inter.y + spacing / 2
            if y < grid_height - 5:
                spawn_points.append((x, y, "UP"))
                despawn_points.append((x, y + 10))

        # Left spawn points (from left column intersections going right)
        for r in range(rows):
            inter = intersections[r * cols]  # first column
            x = inter.x - spacing / 2
            y = inter.y
            if x > 5:
                spawn_points.append((x, y, "RIGHT"))
                despawn_points.append((x - 10, y))

        # Right spawn points (from right column intersections going left)
        for r in range(rows):
            inter = intersections[r * cols + (cols - 1)]  # last column
            x = inter.x + spacing / 2
            y = inter.y
            if x < grid_width - 5:
                spawn_points.append((x, y, "LEFT"))
                despawn_points.append((x + 10, y))

        print(f"Created {len(intersections)} intersections")
        print(f"Created {len(roads)} road segments")
        print(f"Created {len(spawn_points)} spawn points")

        return cls(
            intersections=intersections,
            roads=roads,
            spawn_points=spawn_points,
            despawn_points=despawn_points
        )

    @classmethod
    def from_json(cls, filepath: str) -> 'NetworkConfig':
        """Load network configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        intersections = [
            IntersectionConfig(**item) for item in data['intersections']
        ]
        roads = [
            RoadConfig(**item) for item in data['roads']
        ]

        return cls(
            intersections=intersections,
            roads=roads,
            spawn_points=data.get('spawn_points', []),
            despawn_points=data.get('despawn_points', [])
        )

    def to_json(self, filepath: str):
        """Save network configuration to JSON file"""
        data = {
            'intersections': [
                {
                    'id': i.id,
                    'x': i.x,
                    'y': i.y,
                    'road_type': i.road_type
                }
                for i in self.intersections
            ],
            'roads': [
                {
                    'from_intersection': r.from_intersection,
                    'to_intersection': r.to_intersection,
                    'length': r.length,
                    'lanes': r.lanes
                }
                for r in self.roads
            ],
            'spawn_points': self.spawn_points,
            'despawn_points': self.despawn_points
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)