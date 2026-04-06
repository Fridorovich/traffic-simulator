import React, { useState, useEffect, useCallback } from 'react';
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

  // Обновляем метрики при изменении состояния симуляции
  useEffect(() => {
    if (simulationState && simulationState.metrics) {
      setMetrics(simulationState.metrics);
      setHistoricalMetrics(simulationState.historical_metrics || {});
    }
  }, [simulationState]);

  // Обработчик сообщений от WebSocket
  const handleWebSocketMessage = useCallback((data) => {
    console.log('WebSocket message received at:', new Date().toISOString());
    setSimulationState(data);
  }, []);

  const { isConnected, error: wsError, disconnect } = useWebSocket(
    simulationId,
    handleWebSocketMessage,
    isRunning
  );

  // Обработка ошибок WebSocket
  useEffect(() => {
    if (wsError) {
      console.error('WebSocket error:', wsError);
      setError(`WebSocket connection error: ${wsError}`);
    }
  }, [wsError]);

  useEffect(() => {
    const createNewSimulation = async () => {
      setIsLoading(true);
      try {
        const response = await simulationAPI.createSimulation({
          grid_width: 150,
          grid_height: 150,
          num_vehicles: 20,
          algorithm: 'static',
          spawn_rate: 0.1,
          simulation_speed: 1,
          road_config: 'crossroad',
        });

        const newSimulationId = response.data.simulation_id;
        setSimulationId(newSimulationId);

        const stateResponse = await simulationAPI.getSimulationState(newSimulationId);
        setSimulationState(stateResponse.data);

        setError(null);
      } catch (err) {
        console.error('Error creating simulation:', err);
        setError('Failed to create simulation. Please check if backend is running on http://localhost:8000');
      } finally {
        setIsLoading(false);
      }
    };

    createNewSimulation();

    return () => {
      if (simulationId) {
        disconnect();
      }
    };
  }, []);

  const handleConfigUpdate = async (newConfig) => {
    if (!simulationId) return;

    try {
      await simulationAPI.updateConfig(simulationId, newConfig);
      console.log('Config updated:', newConfig);
    } catch (error) {
      console.error('Error updating config:', error);
      setError('Failed to update configuration');
    }
  };

  const handleAlgorithmChange = async (algorithm) => {
    if (!simulationId) return;

    try {
      await simulationAPI.changeAlgorithm(simulationId, algorithm);
      console.log(`Algorithm changed to: ${algorithm}`);

      // Обновляем состояние после смены алгоритма
      const stateResponse = await simulationAPI.getSimulationState(simulationId);
      setSimulationState(stateResponse.data);
    } catch (error) {
      console.error('Error changing algorithm:', error);
      setError('Failed to change algorithm');
    }
  };

  const handleStep = async () => {
    if (!simulationId) return;

    try {
      // Выполняем один шаг
      await simulationAPI.stepSimulation(simulationId, 1);

      // Обновляем состояние после шага
      const stateResponse = await simulationAPI.getSimulationState(simulationId);
      setSimulationState(stateResponse.data);
    } catch (error) {
      console.error('Error stepping simulation:', error);
      setError('Failed to perform step');
    }
  };

  const handleToggleRunning = async () => {
  if (!simulationId) return;

  try {
    if (!isRunning) {
      console.log('Starting simulation...');
      await simulationAPI.resumeSimulation(simulationId, 1.0);
      setIsRunning(true);
      setError(null);
    } else {
      console.log('Pausing simulation...');
      await simulationAPI.pauseSimulation(simulationId);
      setIsRunning(false);
      setError(null);
    }
  } catch (error) {
    console.error('Error toggling simulation:', error);

    let errorMessage = 'Failed to toggle simulation state';

    if (error.response) {
      errorMessage = `Server error: ${error.response.status} - ${error.response.data?.error || error.response.statusText}`;
      console.error('Server response:', error.response.data);
    } else if (error.request) {
      errorMessage = 'No response from server. Make sure backend is running on http://localhost:8000';
    } else {
      errorMessage = `Request error: ${error.message}`;
    }

    setError(errorMessage);
  }
};

  const handleRestartSimulation = async () => {
    setIsLoading(true);
    setIsRunning(false);

    disconnect();

    try {
      const response = await simulationAPI.createSimulation({
        grid_width: 150,
        grid_height: 150,
        num_vehicles: 20,
        algorithm: 'static',
        spawn_rate: 0.1,
        simulation_speed: 1,
        road_config: 'crossroad',
      });

      const newSimulationId = response.data.simulation_id;
      setSimulationId(newSimulationId);

      const stateResponse = await simulationAPI.getSimulationState(newSimulationId);
      setSimulationState(stateResponse.data);

      setError(null);
    } catch (err) {
      console.error('Error restarting simulation:', err);
      setError('Failed to restart simulation.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCanvasClick = (x, y) => {
    console.log(`Clicked at simulation coordinates: (${x.toFixed(2)}, ${y.toFixed(2)})`);
  };

  if (isLoading) {
    return (
      <div style={styles.loadingContainer}>
        <div style={styles.spinner}></div>
        <p>Initializing traffic simulation...</p>
        <p style={styles.loadingSubtext}>Please wait while we set up the simulation environment</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.errorContainer}>
        <h2 style={styles.errorTitle}>🚨 Error</h2>
        <p style={styles.errorMessage}>{error}</p>
        <p style={styles.errorHint}>Make sure the backend server is running on http://localhost:8000</p>
        <div style={styles.errorActions}>
          <button
            onClick={() => window.location.reload()}
            style={styles.retryButton}
          >
            🔄 Retry
          </button>
          <button
            onClick={handleRestartSimulation}
            style={styles.restartButton}
          >
            🔁 Create New Simulation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <h1 style={styles.title}>🚦 Traffic Light Simulator</h1>
          <div style={styles.simulationId}>ID: {simulationId}</div>
        </div>

        <div style={styles.headerControls}>
          <div style={styles.statusIndicator}>
            <div
              style={{
                ...styles.statusDot,
                backgroundColor: isConnected ? '#2ecc71' : '#e74c3c',
                animation: isConnected ? 'pulse 2s infinite' : 'none',
              }}
            />
            <span style={styles.statusText}>
              {isConnected ? 'Connected' : 'Disconnected'}
              {isRunning && isConnected && ' • Live'}
            </span>
          </div>

          <button
            onClick={handleRestartSimulation}
            style={styles.restartButton}
            title="Create new simulation"
          >
            🔄 New
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
        <p style={styles.footerText}>
          <span>© 2024 Traffic Light Simulator</span>
          <span style={styles.footerSeparator}>•</span>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            style={styles.footerLink}
          >
            📚 API Documentation
          </a>
          <span style={styles.footerSeparator}>•</span>
          <span>Step: {simulationState.steps || 0}</span>
          <span style={styles.footerSeparator}>•</span>
          <span>Vehicles: {simulationState.vehicles?.length || 0}</span>
          <span style={styles.footerSeparator}>•</span>
          <span>Algorithm: {simulationState.config?.algorithm || 'static'}</span>
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
    width: '60px',
    height: '60px',
    border: '6px solid rgba(255,255,255,0.1)',
    borderTop: '6px solid #3498db',
    borderRight: '6px solid #3498db',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: '20px',
  },
  loadingSubtext: {
    marginTop: '10px',
    fontSize: '14px',
    color: '#7f8c8d',
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
  errorTitle: {
    fontSize: '32px',
    marginBottom: '20px',
    color: '#e74c3c',
  },
  errorMessage: {
    fontSize: '18px',
    marginBottom: '10px',
    maxWidth: '600px',
  },
  errorHint: {
    fontSize: '14px',
    color: '#7f8c8d',
    marginBottom: '30px',
  },
  errorActions: {
    display: 'flex',
    gap: '15px',
  },
  retryButton: {
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: 'bold',
    transition: 'all 0.3s ease',
    ':hover': {
      backgroundColor: '#2980b9',
      transform: 'translateY(-2px)',
    },
  },
  header: {
    backgroundColor: '#2c3e50',
    color: 'white',
    padding: '15px 25px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
  },
  title: {
    fontSize: '24px',
    fontWeight: '600',
    margin: 0,
  },
  simulationId: {
    backgroundColor: '#34495e',
    padding: '5px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontFamily: 'monospace',
    color: '#bdc3c7',
  },
  headerControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
  },
  statusIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    backgroundColor: '#34495e',
    padding: '8px 16px',
    borderRadius: '30px',
  },
  statusDot: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    transition: 'background-color 0.3s ease',
  },
  statusText: {
    fontSize: '14px',
    fontWeight: '500',
  },
  restartButton: {
    backgroundColor: '#e67e22',
    color: 'white',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 'bold',
    transition: 'all 0.3s ease',
    ':hover': {
      backgroundColor: '#d35400',
      transform: 'translateY(-2px)',
    },
  },
  main: {
    padding: '25px',
    backgroundColor: '#ecf0f1',
    minHeight: 'calc(100vh - 160px)',
  },
  simulationSection: {
    display: 'grid',
    gridTemplateColumns: '2fr 1fr',
    gap: '25px',
    marginBottom: '25px',
  },
  controlsSection: {},
  metricsSection: {},
  footer: {
    backgroundColor: '#2c3e50',
    color: 'white',
    padding: '12px 25px',
    fontSize: '13px',
  },
  footerText: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
  },
  footerSeparator: {
    color: '#7f8c8d',
    margin: '0 5px',
  },
  footerLink: {
    color: '#3498db',
    textDecoration: 'none',
    transition: 'color 0.3s ease',
    ':hover': {
      color: '#2980b9',
      textDecoration: 'underline',
    },
  },
};

// Добавляем глобальные стили для анимаций
const style = document.createElement('style');
style.textContent = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.6; }
    100% { opacity: 1; }
  }
`;
document.head.appendChild(style);

export default App;