import asyncio
import csv
import time
from src.models.traffic_model import TrafficModel


async def run_experiment(config, duration_steps=1000, warmup_steps=500):
    """Запуск одного эксперимента и сбор метрик"""
    model = TrafficModel(config)

    for _ in range(warmup_steps):
        model.step()

    metrics = []
    for step in range(duration_steps):
        model.step()
        if step % 10 == 0:
            state = model.get_simulation_state()
            metrics.append({
                'step': model.steps,
                'total_vehicles': state['metrics']['total_vehicles'],
                'avg_waiting_time': state['metrics']['avg_waiting_time'],
                'total_delay': state['metrics']['total_delay'],
                'throughput': state['metrics']['throughput'],
                'avg_speed': state['metrics']['avg_speed'],
                'total_stops': state['metrics'].get('total_stops', 0),
                'total_co2_g': state['metrics'].get('total_co2_g', 0),
            })

    return metrics


def save_to_csv(results, filename):
    """Сохранение результатов в CSV"""
    if not results:
        return

    keys = results[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)


async def main():
    scenarios = [
        {
            'name': 'static_crossroad_20',
            'config': {
                'grid_width': 150, 'grid_height': 150,
                'num_vehicles': 20, 'algorithm': 'static',
                'spawn_rate': 0.4, 'road_config': 'crossroad',
                'network_type': 'single'
            }
        },
        {
            'name': 'adaptive_crossroad_20',
            'config': {
                'grid_width': 150, 'grid_height': 150,
                'num_vehicles': 20, 'algorithm': 'adaptive',
                'spawn_rate': 0.4, 'road_config': 'crossroad',
                'network_type': 'single'
            }
        },
        {
            'name': 'static_crossroad_40',
            'config': {
                'grid_width': 150, 'grid_height': 150,
                'num_vehicles': 40, 'algorithm': 'static',
                'spawn_rate': 0.6, 'road_config': 'crossroad',
                'network_type': 'single'
            }
        },
        {
            'name': 'adaptive_crossroad_40',
            'config': {
                'grid_width': 150, 'grid_height': 150,
                'num_vehicles': 40, 'algorithm': 'adaptive',
                'spawn_rate': 0.6, 'road_config': 'crossroad',
                'network_type': 'single'
            }
        },
        {
            'name': 'static_t_intersection_30',
            'config': {
                'grid_width': 150, 'grid_height': 150,
                'num_vehicles': 30, 'algorithm': 'static',
                'spawn_rate': 0.3, 'road_config': 't_intersection',
                'network_type': 'single'
            }
        },
        {
            'name': 'adaptive_t_intersection_30',
            'config': {
                'grid_width': 150, 'grid_height': 150,
                'num_vehicles': 30, 'algorithm': 'adaptive',
                'spawn_rate': 0.3, 'road_config': 't_intersection',
                'network_type': 'single'
            }
        }
    ]

    for scenario in scenarios:
        print(f"Running {scenario['name']}...")
        start_time = time.time()

        all_metrics = []
        for run in range(5):
            print(f"  Run {run + 1}/5")
            metrics = await run_experiment(scenario['config'])
            all_metrics.extend(metrics)

        filename = f"results_{scenario['name']}.csv"
        save_to_csv(all_metrics, filename)

        elapsed = time.time() - start_time
        print(f"  Completed in {elapsed:.1f} seconds. Saved to {filename}")


if __name__ == "__main__":
    asyncio.run(main())