# Traffic Simulator
As part of this work, a web-based traffic control simulator was developed, intended for a comparative analysis of various traffic light control algorithms in a smart city. The simulator is a full-featured application with a client-server architecture that provides interactive simulation and visualization of traffic flows in real time.

## Stack
1. **Backend**: Python + FastAPI + Mesa (agent-based modeling)

2. **Frontend**: React + HTML5 Canvas (interactive visualization)

3. **Communication**: REST API + WebSocket for real-time updates

## 2.2 Key components:
1. **Backend**:
- ```traffic_model.py``` - main simulation model

- ```agents.py``` - agents (vehicles and traffic lights)

- ```algorithms.py``` - implementations of control algorithms

- ```routes.py``` - REST API and WebSocket endpoints

2. **Frontend**:
- ```SimulationCanvas.jsx``` - visualization of simulation on Canvas

- ```ControlPanel.jsx``` - parameters control panel

- ```MetricsDashboard.jsx``` - dashboard with metrics and graphs

- ```useWebSocket.js``` - WebSocket connection for real-time data

## Implemented traffic light control algorithms
1. **Static Algorithm** Description: Basic implementation with fixed time cycles. The algorithm works according to a predetermined schedule without taking into account the current traffic situation.
- Fixed times for each phase: green (30s), yellow (5s), red (35s)
- Cyclic repetition without adaptation
- Phase shift for different directions to prevent simultaneous movement

2. **Adaptive Algorithm** Description: An algorithm that dynamically adapts to the length of the queue of vehicles in front of a traffic light.
- Real-time queue length monitoring
- Automatic green time adjustment
- Smooth adaptation to prevent sudden changes

3. **Coordinated Algorithm** Description: An algorithm that ensures coordination of the operation of several traffic lights to create a “green wave”.
- Synchronization of adjacent traffic lights
- Calculation of optimal phase shifts based on the distance between traffic lights
- Creating conditions for continuous traffic flows
- Taking into account the average speed of movement to calculate the displacement time

## Types of road configurations
1. **Standard Crossroad**
- 4 directions of movement (north, south, west, east)
- 4 traffic lights (one for each direction)
- Possibility of turning in all directions
- Single lane movement in each direction

2. **T-Intersection**
- 3 directions of movement
- 3 traffic lights
- Limited room for maneuver
- Typical for secondary roads

3. **Intersection grid (Grid)**
- Multiple interconnected intersections (2x2 grid)
- 16 traffic lights (4 for each intersection)
- Complex interactions of traffic flows

## Metrics and performance indicators
1. **Key metrics**:
- Average Waiting Time
- Total Delay
- Throughput
- Average Speed

2. **Environmental Metrics**:
- Number of Stops
- Queue Length

3. **Historical data**:
- All metrics are saved with history for the last 100 steps
- Visualize trends through real-time graphs
- Ability to export data for further analysis

## Simulator functionality
1. **Simulation Control**:
- Creating new simulations with custom parameters
- Start/pause real-time simulation
- Step-by-step execution (1, 10, 100 steps)
- Restarting the simulation and saving the configuration

2. **Parameter configuration**:
- Grid size setting (20x20 to 100x100)
- Control of the number of vehicles (1-100)
- Adjusting the flow intensity (spawn rate)
- Selecting the type of road configuration

3. **Visualization**:
- Real-time display of vehicle movement
- Color indication of traffic light status
- Displaying queues in front of traffic lights
- Informative tips and statuses