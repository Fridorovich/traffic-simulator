import React, { useRef, useEffect } from 'react';
import PropTypes from 'prop-types';

const SimulationCanvas = ({
  simulationState,
  isRunning,
  onCanvasClick
}) => {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  const {
    vehicles = [],
    traffic_lights: trafficLights = [],
    config = {}
  } = simulationState;

  const { grid_width: gridWidth = 50, grid_height: gridHeight = 50 } = config;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = '#2c3e50';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = '#34495e';
    ctx.lineWidth = 2;

    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(canvas.width / 2, 0);
    ctx.lineTo(canvas.width / 2, canvas.height);
    ctx.stroke();

    const crossSize = 20;
    ctx.fillStyle = '#7f8c8d';
    ctx.fillRect(
      canvas.width / 2 - crossSize / 2,
      canvas.height / 2 - crossSize / 2,
      crossSize,
      crossSize
    );

    ctx.strokeStyle = '#ecf0f1';
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 10]);

    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(canvas.width / 2, 0);
    ctx.lineTo(canvas.width / 2, canvas.height);
    ctx.stroke();

    ctx.setLineDash([]);

    vehicles.forEach(vehicle => {
      const { x, y, color, speed, waiting_time: waitingTime } = vehicle;

      const scaleX = (x / gridWidth) * canvas.width;
      const scaleY = (y / gridHeight) * canvas.height;

      const size = Math.max(3, Math.min(8, speed * 2));

      const opacity = waitingTime > 0 ? 0.7 : 1;

      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.fillStyle = color;

      ctx.beginPath();
      ctx.arc(scaleX, scaleY, size, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 1;
      ctx.stroke();

      if (speed > 0) {
        ctx.fillStyle = '#fff';
        ctx.font = '8px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(speed.toFixed(1), scaleX, scaleY + size + 10);
      }

      ctx.restore();
    });

    trafficLights.forEach(light => {
      const { x, y, state, direction, queue_length: queueLength } = light;

      const scaleX = (x / gridWidth) * canvas.width;
      const scaleY = (y / gridHeight) * canvas.height;

      const stateColors = {
        RED: '#ff4444',
        YELLOW: '#ffaa00',
        GREEN: '#44ff44',
      };

      const width = direction === 'horizontal' ? 20 : 8;
      const height = direction === 'horizontal' ? 8 : 20;

      ctx.fillStyle = stateColors[state] || '#666';
      ctx.fillRect(
        scaleX - width / 2,
        scaleY - height / 2,
        width,
        height
      );

      ctx.strokeStyle = '#333';
      ctx.lineWidth = 2;
      ctx.strokeRect(
        scaleX - width / 2,
        scaleY - height / 2,
        width,
        height
      );

      if (state === 'YELLOW') {
        ctx.save();
        ctx.globalAlpha = 0.5 + 0.5 * Math.sin(Date.now() / 500);
        ctx.fillStyle = '#fff';
        ctx.fillRect(
          scaleX - width / 2 + 2,
          scaleY - height / 2 + 2,
          width - 4,
          height - 4
        );
        ctx.restore();
      }

      if (queueLength > 0) {
        ctx.fillStyle = 'rgba(255, 100, 100, 0.9)';
        ctx.beginPath();
        ctx.arc(scaleX, scaleY - 15, 10, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 10px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(queueLength.toString(), scaleX, scaleY - 15);
      }
    });
  }, [vehicles, trafficLights, gridWidth, gridHeight, isRunning]);

  const handleCanvasClick = (e) => {
    if (!canvasRef.current || !onCanvasClick) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const simX = (x / rect.width) * gridWidth;
    const simY = (y / rect.height) * gridHeight;

    onCanvasClick(simX, simY);
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '600px',
        backgroundColor: '#1a252f',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
      }}
    >
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          cursor: 'pointer',
        }}
        onClick={handleCanvasClick}
      />

      {isRunning && (
        <div
          style={{
            position: 'absolute',
            top: '10px',
            right: '10px',
            backgroundColor: 'rgba(46, 204, 113, 0.9)',
            color: 'white',
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '14px',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            zIndex: 100,
          }}
        >
          <div
            style={{
              width: '10px',
              height: '10px',
              backgroundColor: '#fff',
              borderRadius: '50%',
              animation: 'pulse 1s infinite',
            }}
          />
          LIVE
        </div>
      )}

      <div
        style={{
          position: 'absolute',
          bottom: '10px',
          left: '10px',
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          color: 'white',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '12px',
          zIndex: 100,
        }}
      >
        <div>Step: {simulationState.steps || 0}</div>
        <div>Vehicles: {vehicles.length}</div>
        <div>Grid: {gridWidth} × {gridHeight}</div>
        {simulationState.config?.algorithm && (
          <div>Algorithm: {simulationState.config.algorithm}</div>
        )}
      </div>

      {!isRunning && (
        <div
          style={{
            position: 'absolute',
            top: '10px',
            left: '10px',
            backgroundColor: 'rgba(231, 76, 60, 0.9)',
            color: 'white',
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '14px',
            fontWeight: 'bold',
            zIndex: 100,
          }}
        >
          ⏸️ PAUSED
        </div>
      )}
    </div>
  );
};

SimulationCanvas.propTypes = {
  simulationState: PropTypes.object.isRequired,
  isRunning: PropTypes.bool.isRequired,
  onCanvasClick: PropTypes.func,
};

export default SimulationCanvas;