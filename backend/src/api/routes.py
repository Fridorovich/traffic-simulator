import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import asyncio
from backend.src.models.traffic_model import TrafficModel
from backend.src.models.algorithms import AlgorithmFactory
import pandas as pd
import numpy as np

app = FastAPI(title="Traffic Simulator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_simulations: Dict[str, TrafficModel] = {}
websocket_connections: Dict[str, List[WebSocket]] = {}
background_tasks: Dict[str, asyncio.Task] = {}


class SimulationConfig(BaseModel):
    grid_width: int = 50
    grid_height: int = 50
    num_vehicles: int = 20
    algorithm: str = "static"
    algorithm_config: Dict[str, Any] = {}
    spawn_rate: float = 0.1
    simulation_speed: float = 1.0
    road_config: str = "crossroad"
    network_type: str = "single"
    network_config: Dict[str, Any] = {}


@app.post("/api/simulation/create")
async def create_simulation(config: SimulationConfig):
    """Create new simulation"""
    sim_id = f"sim_{len(active_simulations)}"
    model = TrafficModel(config.dict())
    active_simulations[sim_id] = model

    return {
        "simulation_id": sim_id,
        "message": "Simulation created successfully",
        "config": config.dict()
    }


@app.post("/api/simulation/{sim_id}/algorithm/change")
async def change_algorithm(sim_id: str, request: Dict):
    """Change control algorithm"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]

    # Извлекаем алгоритм из request
    algorithm = request.get("algorithm")
    config = request.get("config", {})

    if not algorithm:
        return {"error": "Algorithm not specified"}

    # Меняем алгоритм
    model.config["algorithm"] = algorithm
    model.config["algorithm_config"] = config

    # Обновляем алгоритм для всех светофоров
    for light in model.traffic_lights:
        light.algorithm_type = algorithm
        # Сбрасываем таймеры для нового алгоритма
        light.timer = 0
        if algorithm == "static":
            light.green_duration = config.get("green_duration", 30)
            light.yellow_duration = config.get("yellow_duration", 5)
            light.red_duration = config.get("red_duration", 35)
        elif algorithm == "adaptive":
            light.green_duration = config.get("base_green_time", 20)
        elif algorithm == "coordinated":
            light.green_duration = config.get("base_green_time", 25)

    return {
        "message": f"Algorithm changed to {algorithm}",
        "algorithm": algorithm,
        "config": config,
        "current_step": model.steps
    }


@app.get("/api/algorithms")
async def get_algorithms():
    """Get information about available algorithms"""
    return {
        "algorithms": AlgorithmFactory.get_algorithm_info()
    }


@app.get("/api/simulation/{sim_id}/state")
async def get_simulation_state(sim_id: str):
    """Get current simulation state"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]
    return model.get_simulation_state()


@app.post("/api/simulation/{sim_id}/step")
async def simulation_step(sim_id: str, steps: int = 1, collect_metrics: bool = True):
    """Execute simulation steps"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]

    for _ in range(steps):
        model.step()

        if collect_metrics:
            model.datacollector.collect(model)

    return {
        "message": f"Executed {steps} steps",
        "current_step": model.steps,
        "metrics": model.get_simulation_state()["metrics"] if collect_metrics else None
    }


@app.post("/api/simulation/{sim_id}/config")
async def update_config(sim_id: str, config_update: Dict):
    """Update simulation configuration"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]

    allowed_params = [
        "num_vehicles", "spawn_rate", "simulation_speed",
        "road_config", "algorithm_config", "network_type", "network_config",
        "grid_width", "grid_height"
    ]

    # Check if network config changed
    old_network_type = model.config.get("network_type", "single")
    new_network_type = config_update.get("network_type", old_network_type)

    # Check if network parameters changed
    old_network_config = model.config.get("network_config", {"rows": 3, "cols": 3, "spacing": 20})
    new_network_config = config_update.get("network_config", old_network_config)

    # Update config values
    for param in allowed_params:
        if param in config_update:
            model.config[param] = config_update[param]

    # Rebuild network if needed (type changed OR network params changed)
    network_changed = (new_network_type != old_network_type) or (new_network_config != old_network_config)

    if network_changed and new_network_type == "grid":
        # Store new network config
        model.config["network_config"] = new_network_config
        model.config["network_type"] = "grid"
        # Rebuild network with new parameters
        model._rebuild_road_network("grid")
    elif new_network_type == "single" and old_network_type == "grid":
        # Switch from grid to single intersection
        model._rebuild_road_network("single")
    elif "road_config" in config_update and new_network_type == "single":
        # Change intersection type for single mode
        model._rebuild_road_network("single")

    # Handle num_vehicles
    if "num_vehicles" in config_update:
        current_vehicles = len(model.vehicles)
        target_vehicles = config_update["num_vehicles"]

        if target_vehicles > current_vehicles:
            for i in range(target_vehicles - current_vehicles):
                new_id = max([v.unique_id for v in model.vehicles], default=0) + 1
                model._spawn_vehicle(new_id)
        elif target_vehicles < current_vehicles:
            for _ in range(current_vehicles - target_vehicles):
                if model.vehicles:
                    vehicle = model.vehicles[-1]
                    model.vehicles.remove(vehicle)
                    model.schedule.remove(vehicle)
                    model.grid.remove_agent(vehicle)

    # Handle algorithm change
    if "algorithm" in config_update:
        algorithm = config_update["algorithm"]
        algorithm_config = config_update.get("algorithm_config", {})
        model.config["algorithm"] = algorithm
        model.config["algorithm_config"] = algorithm_config

        for light in model.traffic_lights:
            light.algorithm_type = algorithm
            light.timer = 0

    return {
        "message": "Configuration updated successfully",
        "updated_config": {
            "num_vehicles": len(model.vehicles),
            "spawn_rate": model.config.get("spawn_rate"),
            "simulation_speed": model.config.get("simulation_speed"),
            "algorithm": model.config.get("algorithm"),
            "road_config": model.config.get("road_config"),
            "network_type": model.config.get("network_type", "single"),
            "network_config": model.config.get("network_config", {})
        },
        "current_step": model.steps
    }

@app.get("/api/simulation/{sim_id}/agent_metrics")
async def get_agent_metrics(sim_id: str, agent_type: str = "vehicle", limit: int = 50):
    """Get individual agent metrics"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]

    try:
        df = model.datacollector.get_agent_vars_dataframe()
    except Exception as e:
        print(f"Error getting agent vars dataframe: {e}")
        return {"agent_metrics": [], "total_agents": 0}

    if df.empty:
        return {"agent_metrics": [], "total_agents": 0}

    agent_metrics = []

    try:
        if isinstance(df.index, pd.MultiIndex):
            agent_ids = df.index.get_level_values(0).unique()

            for agent_id in agent_ids:
                try:
                    agent_data = df.xs(agent_id, level=0)

                    if not agent_data.empty:
                        latest = agent_data.iloc[-1].to_dict()

                        if agent_type != "all":
                            agent_type_value = latest.get("Type", "")
                            if (agent_type == "vehicle" and "Vehicle" not in agent_type_value) or \
                                    (agent_type == "traffic_light" and "TrafficLight" not in agent_type_value):
                                continue

                        latest["agent_id"] = int(agent_id) if isinstance(agent_id, (int, np.integer)) else str(agent_id)
                        agent_metrics.append(latest)

                except Exception as e:
                    print(f"Error processing agent {agent_id}: {e}")
                    continue
    except Exception as e:
        print(f"Error processing agent metrics: {e}")
        return {"agent_metrics": [], "total_agents": 0}

    return {
        "agent_metrics": agent_metrics[:limit],
        "total_agents": len(agent_metrics)
    }


@app.post("/api/simulation/{sim_id}/pause")
async def pause_simulation(sim_id: str):
    """Pause simulation (set speed to 0)"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]
    model.config["simulation_speed"] = 0.0

    return {
        "message": "Simulation paused",
        "simulation_speed": 0.0
    }


@app.post("/api/simulation/{sim_id}/resume")
async def resume_simulation(sim_id: str, speed: float = 1.0):
    """Resume simulation"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]
    model.config["simulation_speed"] = speed

    return {
        "message": f"Simulation resumed with speed {speed}",
        "simulation_speed": speed
    }


@app.delete("/api/simulation/{sim_id}")
async def delete_simulation(sim_id: str):
    """Delete simulation"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    if sim_id in background_tasks:
        background_tasks[sim_id].cancel()
        del background_tasks[sim_id]

    del active_simulations[sim_id]

    if sim_id in websocket_connections:
        for connection in websocket_connections[sim_id]:
            try:
                await connection.close()
            except:
                pass
        del websocket_connections[sim_id]

    return {"message": f"Simulation {sim_id} deleted successfully"}


async def simulation_updater(sim_id: str):
    """Фоновая задача для отправки обновлений"""
    try:
        while True:
            if sim_id in active_simulations and sim_id in websocket_connections:
                model = active_simulations[sim_id]

                # Проверяем, есть ли активные соединения
                connections = websocket_connections.get(sim_id, [])
                if not connections:
                    await asyncio.sleep(0.1)
                    continue

                # Если симуляция запущена, делаем шаг
                if model.config.get("simulation_speed", 1) > 0:
                    model.step()

                # Получаем текущее состояние
                state = model.get_simulation_state()

                # Отправляем всем подключенным клиентам
                disconnected = []
                for connection in connections:
                    try:
                        await connection.send_json(state)
                    except Exception as e:
                        print(f"Error sending to client: {e}")
                        disconnected.append(connection)

                # Удаляем отключившиеся соединения
                for conn in disconnected:
                    if conn in websocket_connections[sim_id]:
                        websocket_connections[sim_id].remove(conn)

                # Если все соединения отключились, выходим
                if len(websocket_connections[sim_id]) == 0:
                    print(f"No connections left for {sim_id}, stopping background task")
                    break

            # Ждем перед следующим обновлением (30 FPS для уменьшения нагрузки)
            await asyncio.sleep(1 / 30)

    except asyncio.CancelledError:
        print(f"Background task for {sim_id} cancelled")
    except Exception as e:
        print(f"Error in background task for {sim_id}: {e}")


@app.websocket("/ws/simulation/{sim_id}")
async def websocket_endpoint(websocket: WebSocket, sim_id: str):
    """WebSocket for real-time updates"""
    client_id = id(websocket)  # Уникальный ID для каждого соединения
    print(f"New WebSocket connection request for {sim_id} from client {client_id}")

    await websocket.accept()

    print(f"WebSocket accepted for {sim_id} from client {client_id}")

    # Добавляем соединение в список
    if sim_id not in websocket_connections:
        websocket_connections[sim_id] = []

    # Проверяем, нет ли уже такого соединения
    if websocket not in websocket_connections[sim_id]:
        websocket_connections[sim_id].append(websocket)
        print(f"Added client {client_id} to {sim_id}. Total connections: {len(websocket_connections[sim_id])}")
    else:
        print(f"Client {client_id} already in connections")

    # Запускаем фоновую задачу если еще не запущена
    if sim_id not in background_tasks and sim_id in active_simulations:
        task = asyncio.create_task(simulation_updater(sim_id))
        background_tasks[sim_id] = task
        print(f"Started background task for {sim_id}")

    try:
        # Отправляем начальное состояние
        if sim_id in active_simulations:
            model = active_simulations[sim_id]
            state = model.get_simulation_state()
            await websocket.send_json(state)
            print(f"Sent initial state to client {client_id}")

        # Обрабатываем входящие сообщения
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                try:
                    message = json.loads(data)

                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        print(f"Pong sent to client {client_id}")

                except json.JSONDecodeError:
                    pass

            except asyncio.TimeoutError:
                # Проверяем, живо ли соединение
                try:
                    await websocket.send_json({"type": "ping"})
                except:
                    break

            except WebSocketDisconnect:
                print(f"Client {client_id} disconnected normally")
                break
            except Exception as e:
                print(f"Error with client {client_id}: {e}")
                break

    except Exception as e:
        print(f"WebSocket error for client {client_id}: {e}")
    finally:
        # Удаляем соединение
        if sim_id in websocket_connections and websocket in websocket_connections[sim_id]:
            websocket_connections[sim_id].remove(websocket)
            print(f"Removed client {client_id}. Remaining: {len(websocket_connections.get(sim_id, []))}")

        # Если больше нет соединений, останавливаем фоновую задачу
        if sim_id in websocket_connections and len(websocket_connections[sim_id]) == 0:
            if sim_id in background_tasks:
                background_tasks[sim_id].cancel()
                del background_tasks[sim_id]
                print(f"Stopped background task for {sim_id}")

        try:
            await websocket.close()
        except:
            pass


@app.get("/api/simulations")
async def list_simulations():
    """Get list of all active simulations"""
    simulations_list = []

    for sim_id, model in active_simulations.items():
        simulations_list.append({
            "id": sim_id,
            "steps": model.steps,
            "config": {
                "algorithm": model.config.get("algorithm", "static"),
                "num_vehicles": len(model.vehicles),
                "road_config": model.config.get("road_config", "crossroad"),
                "network_type": model.config.get("network_type", "single")
            },
            "metrics": {
                "total_vehicles": len(model.vehicles),
                "avg_waiting_time": model._calculate_avg_waiting_time(),
                "current_step": model.steps
            },
            "connected_clients": len(websocket_connections.get(sim_id, []))
        })

    return {
        "total_simulations": len(active_simulations),
        "simulations": simulations_list
    }


@app.get("/api/simulation/{sim_id}/debug")
async def get_debug_info(sim_id: str):
    """Get debug information about simulation"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]

    debug_info = {
        "simulation_id": sim_id,
        "config": model.config,
        "network_type": model.config.get("network_type", "single"),
        "stats": {
            "total_vehicles": len(model.vehicles),
            "total_traffic_lights": len(model.traffic_lights),
            "completed_vehicles": model.completed_vehicles,
            "spawned_vehicles": model.spawned_vehicles,
            "current_step": model.steps,
            "grid_size": {
                "width": model.config.get("grid_width"),
                "height": model.config.get("grid_height")
            }
        },
        "traffic_lights": [
            {
                "id": light.unique_id,
                "position": light.position,
                "direction": light.direction,
                "side": getattr(light, 'side', None),
                "intersection_type": getattr(light, 'intersection_type', 'crossroad'),
                "state": light.state.value,
                "queue_length": light.get_queue_length()
            }
            for light in model.traffic_lights
        ]
    }

    # Добавляем информацию о сети если есть
    if hasattr(model, 'network') and model.network:
        debug_info["network"] = {
            "intersections_count": len(model.network.intersections),
            "roads_count": len(model.network.roads),
            "intersections": [
                {
                    "id": node.id,
                    "x": node.x,
                    "y": node.y,
                    "traffic_lights_count": len(node.traffic_lights)
                }
                for node in model.network.intersections.values()
            ]
        }

    return debug_info


@app.get("/api/simulation/{sim_id}/traffic_lights")
async def get_traffic_lights_info(sim_id: str):
    """Get detailed traffic lights information"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]

    return {
        "total": len(model.traffic_lights),
        "traffic_lights": [
            {
                "id": light.unique_id,
                "x": light.position[0],
                "y": light.position[1],
                "direction": light.direction,
                "side": getattr(light, 'side', None),
                "intersection_type": getattr(light, 'intersection_type', 'crossroad'),
                "state": light.state.value,
                "queue_length": light.get_queue_length(),
                "green_duration": light.green_duration,
                "yellow_duration": light.yellow_duration,
                "red_duration": light.red_duration
            }
            for light in model.traffic_lights
        ]
    }