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
    grid_width: 150,
    grid_height: 150,
    road_config: 'crossroad',
    algorithm_config: {},
    network_type: 'single',
    network_config: {
      rows: 3,
      cols: 3,
      spacing: 20
    }
  });

  const [algorithms, setAlgorithms] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [updateStatus, setUpdateStatus] = useState('');

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

  const handleConfigChange = async (key, value) => {
    const newConfig = { ...config, [key]: value };
    setConfig(newConfig);

    if (onConfigUpdate) {
      setUpdateStatus('updating...');
      try {
        await onConfigUpdate(newConfig);
        setUpdateStatus('updated ✓');
        setTimeout(() => setUpdateStatus(''), 2000);
      } catch (error) {
        setUpdateStatus('error!');
        console.error('Error updating config:', error);
      }
    }
  };

  const handleNetworkConfigChange = async (key, value) => {
      const newNetworkConfig = { ...config.network_config, [key]: value };
      setConfig(prev => ({ ...prev, network_config: newNetworkConfig }));

      // Всегда отправляем обновление на сервер при изменении параметров сетки
      if (onConfigUpdate) {
        setUpdateStatus('updating network...');
        try {
          await onConfigUpdate({
            ...config,
            network_config: newNetworkConfig,
            network_type: 'grid'
          });
          setUpdateStatus('network updated ✓');
          setTimeout(() => setUpdateStatus(''), 2000);
        } catch (error) {
          setUpdateStatus('error!');
          console.error('Error updating network config:', error);
        }
      }
    };

  const handleNetworkToggle = async () => {
    const newNetworkType = config.network_type === 'single' ? 'grid' : 'single';

    if (onConfigUpdate) {
      setUpdateStatus(newNetworkType === 'grid' ? 'activating grid...' : 'deactivating grid...');
      try {
        await onConfigUpdate({
          ...config,
          network_type: newNetworkType,
          network_config: config.network_config
        });
        setConfig(prev => ({ ...prev, network_type: newNetworkType }));
        setUpdateStatus(newNetworkType === 'grid' ? 'grid activated ✓' : 'grid deactivated ✓');
        setTimeout(() => setUpdateStatus(''), 2000);
      } catch (error) {
        setUpdateStatus('error!');
        console.error('Error toggling network:', error);
      }
    }
  };

  const handleAlgorithmChange = async (algorithmId) => {
    if (!simulationId) return;

    setIsLoading(true);
    setUpdateStatus('changing algorithm...');

    try {
      const selectedAlgo = algorithms.find(a => a.id === algorithmId);
      const algoConfig = {};
      if (selectedAlgo && selectedAlgo.parameters) {
        selectedAlgo.parameters.forEach(param => {
          algoConfig[param.name] = param.default;
        });
      }

      await simulationAPI.changeAlgorithm(simulationId, algorithmId, algoConfig);
      setConfig(prev => ({ ...prev, algorithm: algorithmId, algorithm_config: algoConfig }));

      if (onAlgorithmChange) {
        onAlgorithmChange(algorithmId);
      }

      setUpdateStatus('algorithm changed ✓');
      setTimeout(() => setUpdateStatus(''), 2000);
    } catch (error) {
      console.error('Error changing algorithm:', error);
      setUpdateStatus('error changing algorithm!');
      if (error.response) {
        console.error('Server response:', error.response.data);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleStep = async () => {
    if (!simulationId) return;

    try {
      setUpdateStatus('stepping...');
      await simulationAPI.stepSimulation(simulationId, 1);
      if (onStep) {
        onStep();
      }
      setUpdateStatus('step completed ✓');
      setTimeout(() => setUpdateStatus(''), 1000);
    } catch (error) {
      console.error('Error stepping simulation:', error);
      setUpdateStatus('step error!');
    }
  };

  return (
    <div style={{
      backgroundColor: 'white',
      borderRadius: '8px',
      padding: '20px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    }}>
      <h3 style={{ marginBottom: '20px', color: '#2c3e50', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>⚙️ Control Panel</span>
        {updateStatus && (
          <span style={{ fontSize: '12px', color: updateStatus.includes('error') ? '#e74c3c' : '#27ae60' }}>
            {updateStatus}
          </span>
        )}
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
          ⏭️ Single Step
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

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>
          Road Configuration
        </label>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
          {['crossroad', 't_intersection'].map(type => (
            <button
              key={type}
              onClick={() => handleConfigChange('road_config', type)}
              disabled={config.network_type !== 'single'}
              style={{
                backgroundColor: config.road_config === type && config.network_type === 'single' ? '#3498db' : '#ecf0f1',
                color: config.road_config === type && config.network_type === 'single' ? 'white' : '#2c3e50',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '6px',
                cursor: config.network_type === 'single' ? 'pointer' : 'not-allowed',
                fontSize: '13px',
                flex: 1,
                textTransform: 'capitalize',
                opacity: config.network_type !== 'single' ? 0.5 : 1,
              }}
              title={config.network_type !== 'single' ? 'Disabled in network mode' : ''}
            >
              {type === 'crossroad' ? '4-Way Intersection' : 'T-Intersection'}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: '600' }}>
          🕸️ Network Mode
        </label>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            onClick={handleNetworkToggle}
            style={{
              backgroundColor: config.network_type === 'grid' ? '#3498db' : '#ecf0f1',
              color: config.network_type === 'grid' ? 'white' : '#2c3e50',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              flex: 1,
              fontSize: '13px',
              fontWeight: 'bold',
            }}
          >
            {config.network_type === 'grid' ? '🌐 Grid Network ON' : '📍 Single Intersection'}
          </button>
        </div>

        {config.network_type === 'grid' && (
          <div style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f8f9fa', borderRadius: '6px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '10px' }}>
              <SliderControl
                label="Rows"
                value={config.network_config.rows}
                min={2}
                max={5}
                step={1}
                onChange={(v) => handleNetworkConfigChange('rows', v)}
              />
              <SliderControl
                label="Cols"
                value={config.network_config.cols}
                min={2}
                max={5}
                step={1}
                onChange={(v) => handleNetworkConfigChange('cols', v)}
              />
              <SliderControl
                label="Spacing"
                value={config.network_config.spacing}
                min={15}
                max={35}
                step={2}
                onChange={(v) => handleNetworkConfigChange('spacing', v)}
              />
            </div>
            <div style={{ fontSize: '12px', color: '#7f8c8d', textAlign: 'center' }}>
              Grid will create {config.network_config.rows} × {config.network_config.cols} intersections
            </div>
          </div>
        )}
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
          min={30}
          max={150}
          step={10}
          onChange={(value) => handleConfigChange('grid_width', value)}
        />

        <SliderControl
          label="Grid Height"
          value={config.grid_height}
          min={30}
          max={150}
          step={10}
          onChange={(value) => handleConfigChange('grid_height', value)}
        />
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