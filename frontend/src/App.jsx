import React, { useState, useEffect, useRef } from 'react';
import SimulationCanvas from './components/SimulationCanvas';
import ControlPanel from './components/ControlPanel';
import MetricsDashboard from './components/MetricsDashboard';
import useWebSocket from './hooks/useWebSocket';
import { simulationAPI } from './services/api';
import './App.css';

function App() {
  const [simulationId, setSimulationId] = useState(null);
  const [simulationState, setSimulationState] = useState({});
  const [metrics, setMetrics] = useState({});
  const [historicalMetrics, setHistoricalMetrics] = useState({});
  const [isRunning, setIsRunning] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const { isConnected, sendStep } = useWebSocket(
    simulationId,
    (data) => {
      setSimulationState(data);
      setMetrics(data.metrics || {});
      setHistoricalMetrics(data.historical_metrics || {});
    },
    isRunning
  );

  useEffect(() => {
    const createNewSimulation = async () => {
      setIsLoading(true);
      try {
        const response = await simulationAPI.createSimulation({
          grid_width: 50,
          grid_height: 50,
          num_vehicles: 20,
          algorithm: 'static',
          spawn_rate: 0.1,
          simulation_speed: 1,
          road_config: 'crossroad',
        });

        setSimulationId(response.data.simulation_id);

        const stateResponse = await simulationAPI.getSimulationState(
          response.data.simulation_id
        );
        setSimulationState(stateResponse.data);

        const metricsResponse = await simulationAPI.getMetrics(
          response.data.simulation_id
        );
        setMetrics(metricsResponse.data.current_metrics || {});
        setHistoricalMetrics(stateResponse.data.historical_metrics || {});

        setError(null);
      } catch (err) {
        console.error('Error creating simulation:', err);
        setError('Failed to create simulation. Please check if backend is running.');
      } finally {
        setIsLoading(false);
      }
    };

    createNewSimulation();
  }, []);

  const handleConfigUpdate = async (newConfig) => {
    if (!simulationId) return;

    try {
      await simulationAPI.updateConfig(simulationId, newConfig);
    } catch (error) {
      console.error('Error updating config:', error);
    }
  };

  const handleAlgorithmChange = async (algorithm) => {
    if (!simulationId) return;

    try {
      await simulationAPI.changeAlgorithm(simulationId, algorithm);
      console.log(`Algorithm changed to: ${algorithm}`);
    } catch (error) {
      console.error('Error changing algorithm:', error);
    }
  };

  const handleStep = async () => {
    if (!simulationId) return;

    try {
      if (isConnected) {
        sendStep();
      } else {
        await simulationAPI.stepSimulation(simulationId, 10);
        const stateResponse = await simulationAPI.getSimulationState(simulationId);
        setSimulationState(stateResponse.data);
      }
    } catch (error) {
      console.error('Error stepping simulation:', error);
    }
  };

  const handleToggleRunning = () => {
    setIsRunning(!isRunning);
  };

  const handleCanvasClick = (x, y) => {
    console.log(`Clicked at: (${x.toFixed(2)}, ${y.toFixed(2)})`);
  };

  const handleRestartSimulation = async () => {
    setIsLoading(true);
    setIsRunning(false);

    try {
      const response = await simulationAPI.createSimulation({
        grid_width: 50,
        grid_height: 50,
        num_vehicles: 20,
        algorithm: 'static',
        spawn_rate: 0.1,
        simulation_speed: 1,
        road_config: 'crossroad',
      });

      setSimulationId(response.data.simulation_id);

      const stateResponse = await simulationAPI.getSimulationState(
        response.data.simulation_id
      );
      setSimulationState(stateResponse.data);

      setError(null);
    } catch (err) {
      console.error('Error restarting simulation:', err);
      setError('Failed to restart simulation.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.spinner}></div>
        <p>Initializing traffic simulation...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.errorContainer}>
        <h2>🚨 Error</h2>
        <p>{error}</p>
        <p>Make sure the backend server is running on http://localhost:8000</p>
        <button
          onClick={() => window.location.reload()}
          style={styles.retryButton}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="App">
      <header style={styles.header}>
        <h1>🚦 Traffic Light Simulator</h1>
        <div style={styles.headerControls}>
          <div style={styles.statusIndicator}>
            <div
              style={{
                ...styles.statusDot,
                backgroundColor: isConnected ? '#2ecc71' : '#e74c3c'
              }}
            />
            <span>
              {isConnected ? 'Connected' : 'Disconnected'}
              {isRunning && ' • Live'}
            </span>
          </div>
          <button
            onClick={handleRestartSimulation}
            style={styles.restartButton}
          >
            🔄 Restart
          </button>
        </div>
      </header>

      <main style={styles.main}>
        <div style={styles.simulationSection}>
          <SimulationCanvas
            simulationState={simulationState}
            isRunning={isRunning}
            onCanvasClick={handleCanvasClick}
          />

          <div style={styles.controlsSection}>
            <ControlPanel
              simulationId={simulationId}
              onConfigUpdate={handleConfigUpdate}
              onAlgorithmChange={handleAlgorithmChange}
              onStep={handleStep}
              isRunning={isRunning}
              onToggleRunning={handleToggleRunning}
            />
          </div>
        </div>

        <div style={styles.metricsSection}>
          <MetricsDashboard
            metrics={metrics}
            historicalMetrics={historicalMetrics}
          />
        </div>
      </main>

      <footer style={styles.footer}>
        <p>
          Traffic Light Algorithms Simulation •
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            style={styles.link}
          >
            API Documentation
          </a>
          • Step: {simulationState.steps || 0}
          • Vehicles: {simulationState.vehicles?.length || 0}
        </p>
      </footer>
    </div>
  );
}

const styles = {
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    backgroundColor: '#1a252f',
    color: 'white',
  },
  spinner: {
    width: '50px',
    height: '50px',
    border: '5px solid #f3f3f3',
    borderTop: '5px solid #3498db',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: '20px',
  },
  errorContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    backgroundColor: '#1a252f',
    color: 'white',
    padding: '20px',
    textAlign: 'center',
  },
  retryButton: {
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '16px',
    marginTop: '20px',
  },
  header: {
    backgroundColor: '#2c3e50',
    color: 'white',
    padding: '15px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '15px',
  },
  statusIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
  },
  statusDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
  },
  restartButton: {
    backgroundColor: '#e67e22',
    color: 'white',
    border: 'none',
    padding: '8px 15px',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
  },
  main: {
    padding: '20px',
    backgroundColor: '#ecf0f1',
    minHeight: 'calc(100vh - 140px)',
  },
  simulationSection: {
    display: 'grid',
    gridTemplateColumns: '2fr 1fr',
    gap: '20px',
    marginBottom: '20px',
  },
  controlsSection: {},
  metricsSection: {},
  footer: {
    backgroundColor: '#2c3e50',
    color: 'white',
    padding: '10px 20px',
    textAlign: 'center',
    fontSize: '14px',
  },
  link: {
    color: '#3498db',
    margin: '0 10px',
    textDecoration: 'none',
  },
};

export default App;