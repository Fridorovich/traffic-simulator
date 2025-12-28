import React from 'react';
import PropTypes from 'prop-types';

const Vehicle = ({ vehicle, gridWidth, gridHeight }) => {
  const { x, y, color, speed, waiting_time: waitingTime } = vehicle;

  const scaleX = (x / gridWidth) * 100;
  const scaleY = (y / gridHeight) * 100;

  const size = Math.max(2, Math.min(5, speed * 2));

  const opacity = waitingTime > 0 ? 0.7 : 1;

  return (
    <div
      className="vehicle"
      style={{
        position: 'absolute',
        left: `${scaleX}%`,
        top: `${scaleY}%`,
        width: `${size}px`,
        height: `${size}px`,
        backgroundColor: color,
        borderRadius: '50%',
        transform: 'translate(-50%, -50%)',
        opacity: opacity,
        boxShadow: waitingTime > 0
          ? `0 0 8px ${color}`
          : `0 0 4px ${color}`,
        transition: 'all 0.1s ease',
        zIndex: 10,
      }}
      title={`Speed: ${speed.toFixed(2)}\nWaiting: ${waitingTime}s`}
    />
  );
};

Vehicle.propTypes = {
  vehicle: PropTypes.shape({
    x: PropTypes.number.isRequired,
    y: PropTypes.number.isRequired,
    color: PropTypes.string.isRequired,
    speed: PropTypes.number.isRequired,
    waiting_time: PropTypes.number.isRequired,
  }).isRequired,
  gridWidth: PropTypes.number.isRequired,
  gridHeight: PropTypes.number.isRequired,
};

export default Vehicle;