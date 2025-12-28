import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { simulationAPI } from '../services/api';

const ControlPanel = ({
  simulationId,
  onConfigUpdate,
  onAlgorithmChange,
  onStep,
  isRunning,
  onToggleRunning
}) => {
  const [config, setConfig] = useState({
    num_vehicles: 20,
    spawn_rate: 0.1,
    simulation_speed: 1,
    algorithm: 'static',
    grid_width: 50,
    grid_height: 50,
    road_config: 'crossroad',
  });

  const [algorithms, setAlgorithms] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const loadAlgorithms = async () => {
      try {
        const response = await simulationAPI.getAlgorithms();
        setAlgorithms(response.data.algorithms || []);
      } catch (error) {
        console.error('Error loading algorithms:', error);
      }
    };

    loadAlgorithms();
  }, []);

  const handleConfigChange = (key, value) => {
    const newConfig = { ...config, [key]: value };
    setConfig(newConfig);
    if (onConfigUpdate) {
      onConfigUpdate(newConfig);
    }
  };

  const handleAlgorithmChange = async (algorithm) => {
    if (!simulationId) return;

    setIsLoading(true);
    try {
      await simulationAPI.changeAlgorithm(simulationId, algorithm);
      handleConfigChange('algorithm', algorithm);
      if (onAlgorithmChange) {
        onAlgorithmChange(algorithm);
      }
    } catch (error) {
      console.error('Error changing algorithm:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleStep = async () => {
    if (!simulationId) return;

    try {
      await simulationAPI.stepSimulation(simulationId, 10);
      if (onStep) {
        onStep();
      }
    } catch (error) {
      console.error('Error stepping simulation:', error);
    }
  };

  return (
    <div style={{
      backgroundColor: 'white',
      borderRadius: '8px',
      padding: '20px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    }}>
      <h3 style={{ marginBottom: '20px', color: '#2c3e50' }}>
        ⚙️ Control Panel
      </h3>

      <div style={{ marginBottom: '20px' }}>
        <button
          onClick={onToggleRunning}
          style={{
            backgroundColor: isRunning ? '#e74c3c' : '#2ecc71',
            color: 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
            marginRight: '10px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          {isRunning ? (
            <>
              <span>⏸️</span> Pause
            </>
          ) : (
            <>
              <span>▶️</span> Start Live
            </>
          )}
        </button>

        <button
          onClick={handleStep}
          disabled={isRunning}
          style={{
            backgroundColor: '#3498db',
            color: 'white',
            border: 'none',
            padding: '10px 20px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
            opacity: isRunning ? 0.5 : 1,
          }}
        >
          ⏭️ Step +10
        </button>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>
          Algorithm
        </label>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {algorithms.map(algo => (
            <button
              key={algo.id}
              onClick={() => handleAlgorithmChange(algo.id)}
              disabled={isLoading || config.algorithm === algo.id}
              style={{
                backgroundColor: config.algorithm === algo.id ? '#3498db' : '#ecf0f1',
                color: config.algorithm === algo.id ? 'white' : '#2c3e50',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: config.algorithm === algo.id ? 'bold' : 'normal',
                flex: 1,
                minWidth: '120px',
                opacity: isLoading ? 0.5 : 1,
              }}
              title={algo.description}
            >
              {algo.name}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <SliderControl
          label="Number of Vehicles"
          value={config.num_vehicles}
          min={1}
          max={100}
          step={1}
          onChange={(value) => handleConfigChange('num_vehicles', value)}
        />

        <SliderControl
          label="Spawn Rate"
          value={config.spawn_rate}
          min={0}
          max={1}
          step={0.05}
          onChange={(value) => handleConfigChange('spawn_rate', value)}
          formatValue={(value) => `${(value * 100).toFixed(0)}%`}
        />

        <SliderControl
          label="Simulation Speed"
          value={config.simulation_speed}
          min={0.1}
          max={5}
          step={0.1}
          onChange={(value) => handleConfigChange('simulation_speed', value)}
          formatValue={(value) => `${value.toFixed(1)}x`}
        />

        <SliderControl
          label="Grid Width"
          value={config.grid_width}
          min={20}
          max={100}
          step={10}
          onChange={(value) => handleConfigChange('grid_width', value)}
        />

        <SliderControl
          label="Grid Height"
          value={config.grid_height}
          min={20}
          max={100}
          step={10}
          onChange={(value) => handleConfigChange('grid_height', value)}
        />
      </div>

      <div style={{ marginTop: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>
          Road Configuration
        </label>
        <div style={{ display: 'flex', gap: '10px' }}>
          {['crossroad', 't_intersection', 'grid'].map(type => (
            <button
              key={type}
              onClick={() => handleConfigChange('road_config', type)}
              style={{
                backgroundColor: config.road_config === type ? '#3498db' : '#ecf0f1',
                color: config.road_config === type ? 'white' : '#2c3e50',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '13px',
                flex: 1,
                textTransform: 'capitalize',
              }}
            >
              {type.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

const SliderControl = ({
  label,
  value,
  min,
  max,
  step,
  onChange,
  formatValue
}) => {
  const handleChange = (e) => {
    onChange(parseFloat(e.target.value));
  };

  return (
    <div>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        marginBottom: '5px',
      }}>
        <label style={{ fontSize: '14px', fontWeight: '600' }}>
          {label}
        </label>
        <span style={{ fontSize: '14px', color: '#7f8c8d' }}>
          {formatValue ? formatValue(value) : value}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={handleChange}
        style={{
          width: '100%',
          height: '6px',
          borderRadius: '3px',
          backgroundColor: '#dfe6e9',
          outline: 'none',
        }}
      />
    </div>
  );
};

ControlPanel.propTypes = {
  simulationId: PropTypes.string,
  onConfigUpdate: PropTypes.func,
  onAlgorithmChange: PropTypes.func,
  onStep: PropTypes.func,
  isRunning: PropTypes.bool,
  onToggleRunning: PropTypes.func,
};

SliderControl.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.number.isRequired,
  min: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired,
  step: PropTypes.number.isRequired,
  onChange: PropTypes.func.isRequired,
  formatValue: PropTypes.func,
};

export default ControlPanel;