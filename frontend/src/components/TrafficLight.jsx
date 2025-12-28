import React from 'react';
import PropTypes from 'prop-types';

const TrafficLight = ({ light, gridWidth, gridHeight }) => {
  const { x, y, state, direction, queue_length: queueLength } = light;

  const scaleX = (x / gridWidth) * 100;
  const scaleY = (y / gridHeight) * 100;

  const stateColors = {
    RED: '#ff4444',
    YELLOW: '#ffaa00',
    GREEN: '#44ff44',
  };

  const size = direction === 'horizontal' ? 20 : 8;
  const width = direction === 'horizontal' ? 8 : 20;

  return (
    <div
      className="traffic-light"
      style={{
        position: 'absolute',
        left: `${scaleX}%`,
        top: `${scaleY}%`,
        width: `${width}px`,
        height: `${size}px`,
        backgroundColor: stateColors[state] || '#666',
        borderRadius: '4px',
        transform: 'translate(-50%, -50%)',
        border: '2px solid #333',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 5,
        boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
      }}
      title={`State: ${state}\nQueue: ${queueLength}\nDirection: ${direction}`}
    >
      {queueLength > 0 && (
        <div
          style={{
            position: 'absolute',
            top: '-20px',
            backgroundColor: 'rgba(255, 100, 100, 0.9)',
            color: 'white',
            padding: '2px 6px',
            borderRadius: '10px',
            fontSize: '12px',
            fontWeight: 'bold',
          }}
        >
          {queueLength}
        </div>
      )}

      {state === 'YELLOW' && (
        <div
          style={{
            animation: 'blink 1s infinite',
            fontSize: '10px',
            color: '#000',
            fontWeight: 'bold',
          }}
        >
          ●
        </div>
      )}
    </div>
  );
};

TrafficLight.propTypes = {
  light: PropTypes.shape({
    x: PropTypes.number.isRequired,
    y: PropTypes.number.isRequired,
    state: PropTypes.string.isRequired,
    direction: PropTypes.string.isRequired,
    queue_length: PropTypes.number.isRequired,
  }).isRequired,
  gridWidth: PropTypes.number.isRequired,
  gridHeight: PropTypes.number.isRequired,
};

export default TrafficLight;