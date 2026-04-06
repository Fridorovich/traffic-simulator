from typing import List, Tuple, Dict, Optional
import heapq


class PathFinder:
    """A* path finding for road network"""

    def __init__(self, network):
        self.network = network

    def find_path(self, start_node_id: int, end_node_id: int) -> Optional[List[int]]:
        """Find path from start node to end node using A*"""

        def heuristic(node_id: int) -> float:
            """Euclidean distance to goal as heuristic"""
            start = self.network.get_intersection(node_id)
            goal = self.network.get_intersection(end_node_id)
            return ((start.x - goal.x) ** 2 + (start.y - goal.y) ** 2) ** 0.5

        open_set = [(0, start_node_id)]
        came_from = {}
        g_score = {start_node_id: 0}
        f_score = {start_node_id: heuristic(start_node_id)}

        while open_set:
            current = heapq.heappop(open_set)[1]

            if current == end_node_id:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_node_id)
                return list(reversed(path))

            for neighbor in self.network.get_neighbors(current):
                tentative_g = g_score[current] + 1  # Uniform cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return None

    def get_random_path(self, start_node_id: int, possible_destinations: List[int]) -> Optional[List[int]]:
        """Get random path to a random destination"""
        import random
        if not possible_destinations:
            return None

        end_node_id = random.choice(possible_destinations)
        if start_node_id == end_node_id:
            # Choose different destination
            others = [d for d in possible_destinations if d != start_node_id]
            if others:
                end_node_id = random.choice(others)
            else:
                return None

        return self.find_path(start_node_id, end_node_id)