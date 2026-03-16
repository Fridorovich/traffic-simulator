import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import asyncio
from backend.src.models.traffic_model import TrafficModel
from backend.src.models.algorithms import AlgorithmFactory

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
async def change_algorithm(sim_id: str, algorithm: str, config: Dict = None):
    """Change control algorithm"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]
    model.change_algorithm(algorithm, config or {})

    return {
        "message": f"Algorithm changed to {algorithm}",
        "algorithm": algorithm,
        "config": config
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
        "road_config", "algorithm_config"
    ]

    for param in allowed_params:
        if param in config_update:
            model.config[param] = config_update[param]

    if "algorithm" in config_update:
        algorithm_config = config_update.get("algorithm_config", {})
        model.change_algorithm(config_update["algorithm"], algorithm_config)

    return {
        "message": "Configuration updated successfully",
        "updated_config": {k: v for k, v in model.config.items() if k in allowed_params or k == "algorithm"},
        "current_step": model.steps
    }


@app.get("/api/simulation/{sim_id}/metrics")
async def get_metrics(sim_id: str, limit: int = 100, aggregated: bool = False):
    """Get simulation metrics"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]

    if aggregated:
        df = model.datacollector.get_model_vars_dataframe()

        if df.empty:
            return {"metrics": [], "aggregated": {}}

        recent_df = df.tail(limit)

        aggregated_metrics = {
            "avg_waiting_time": float(recent_df["Avg_Waiting_Time"].mean()),
            "max_waiting_time": float(recent_df["Avg_Waiting_Time"].max()),
            "min_waiting_time": float(recent_df["Avg_Waiting_Time"].min()),
            "avg_delay": float(recent_df["Total_Delay"].mean()),
            "max_delay": float(recent_df["Total_Delay"].max()),
            "total_throughput": int(recent_df["Throughput"].sum()),
            "avg_speed": float(recent_df["Avg_Speed"].mean()),
            "avg_vehicles": float(recent_df["Total_Vehicles"].mean()),
            "algorithm": model.config["algorithm"]
        }

        return {
            "metrics": recent_df.to_dict(orient="records"),
            "aggregated": aggregated_metrics,
            "current_step": model.steps
        }
    else:
        df = model.datacollector.get_model_vars_dataframe()
        return {
            "metrics": df.tail(limit).to_dict(orient="records"),
            "current_step": model.steps
        }


@app.get("/api/simulation/{sim_id}/agent_metrics")
async def get_agent_metrics(sim_id: str, agent_type: str = "vehicle", limit: int = 50):
    """Get individual agent metrics"""
    if sim_id not in active_simulations:
        return {"error": "Simulation not found"}

    model = active_simulations[sim_id]
    df = model.datacollector.get_agent_vars_dataframe()

    if df.empty:
        return {"agent_metrics": []}

    if agent_type == "vehicle":
        filtered_df = df[df["Type"] == "VehicleAgent"]
    elif agent_type == "traffic_light":
        filtered_df = df[df["Type"] == "TrafficLightAgent"]
    else:
        filtered_df = df

    agent_metrics = []
    if not filtered_df.empty:
        for agent_id in filtered_df.index.levels[0]:
            agent_data = filtered_df.xs(agent_id)
            if not agent_data.empty:
                latest = agent_data.iloc[-1].to_dict()
                latest["agent_id"] = agent_id
                agent_metrics.append(latest)

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
                "road_config": model.config.get("road_config", "crossroad")
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