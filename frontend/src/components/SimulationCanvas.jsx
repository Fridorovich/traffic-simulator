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
    network = null,
    config = {}
  } = simulationState;

  const {
    grid_width: gridWidth = 150,
    grid_height: gridHeight = 150,
    road_config: roadConfig = 'crossroad',
    network_type: networkType = 'single'
  } = config;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Устанавливаем фиксированный размер canvas
    canvas.width = 800;
    canvas.height = 600;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Фон
    ctx.fillStyle = '#2c3e50';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Простые функции масштабирования
    const scaleX = (x) => (x / gridWidth) * canvas.width;
    const scaleY = (y) => (y / gridHeight) * canvas.height;

    const roadWidth = 20;
    const crossSize = 25;

    ctx.fillStyle = '#34495e';

    // ========== ОТРИСОВКА ДОРОГ И ПЕРЕКРЕСТКОВ ==========
    if (networkType === 'grid' && network && network.intersections && network.intersections.length > 0) {
      // Сетка перекрестков
      const intersections = network.intersections;

      // Создаем карту уникальных координат для дорог
      const horizontalRoads = new Map();
      const verticalRoads = new Map();

      intersections.forEach(intersection => {
        const x = intersection.x;
        const y = intersection.y;

        if (!horizontalRoads.has(y)) {
          horizontalRoads.set(y, []);
        }
        horizontalRoads.get(y).push(x);

        if (!verticalRoads.has(x)) {
          verticalRoads.set(x, []);
        }
        verticalRoads.get(x).push(y);
      });

      // Рисуем горизонтальные дороги
      horizontalRoads.forEach((xs, y) => {
        if (xs.length >= 2) {
          xs.sort((a, b) => a - b);
          const minX = Math.min(...xs);
          const maxX = Math.max(...xs);
          const screenY = scaleY(y);
          const screenStartX = scaleX(minX);
          const screenEndX = scaleX(maxX);
          ctx.fillRect(screenStartX - roadWidth/2, screenY - roadWidth/2,
                       screenEndX - screenStartX + roadWidth, roadWidth);
        }
      });

      // Рисуем вертикальные дороги
      verticalRoads.forEach((ys, x) => {
        if (ys.length >= 2) {
          ys.sort((a, b) => a - b);
          const minY = Math.min(...ys);
          const maxY = Math.max(...ys);
          const screenX = scaleX(x);
          const screenStartY = scaleY(minY);
          const screenEndY = scaleY(maxY);
          ctx.fillRect(screenX - roadWidth/2, screenStartY - roadWidth/2,
                       roadWidth, screenEndY - screenStartY + roadWidth);
        }
      });

      // Рисуем перекрестки
      intersections.forEach(intersection => {
        const screenX = scaleX(intersection.x);
        const screenY = scaleY(intersection.y);

        ctx.fillStyle = '#7f8c8d';
        ctx.fillRect(
          screenX - crossSize/2,
          screenY - crossSize/2,
          crossSize,
          crossSize
        );

        ctx.strokeStyle = '#ecf0f1';
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 10]);

        ctx.beginPath();
        ctx.moveTo(screenX - crossSize/2, screenY);
        ctx.lineTo(screenX + crossSize/2, screenY);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(screenX, screenY - crossSize/2);
        ctx.lineTo(screenX, screenY + crossSize/2);
        ctx.stroke();

        ctx.setLineDash([]);
      });

    } else if (roadConfig === 't_intersection' && networkType !== 'grid') {
      // T-образный перекресток
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      ctx.fillStyle = '#34495e';
      ctx.fillRect(0, centerY - roadWidth/2, canvas.width, roadWidth);
      ctx.fillRect(centerX - roadWidth/2, centerY, roadWidth, canvas.height - centerY);

      ctx.fillStyle = '#7f8c8d';
      ctx.fillRect(
        centerX - crossSize / 2,
        centerY - crossSize / 2,
        crossSize,
        crossSize
      );

      ctx.strokeStyle = '#ecf0f1';
      ctx.lineWidth = 1;
      ctx.setLineDash([5, 10]);

      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(canvas.width, centerY);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(centerX, 0);
      ctx.lineTo(centerX, canvas.height);
      ctx.stroke();

      ctx.setLineDash([]);

    } else if (networkType !== 'grid') {
      // Обычный перекресток
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;

      ctx.fillStyle = '#34495e';
      ctx.fillRect(0, centerY - roadWidth/2, canvas.width, roadWidth);
      ctx.fillRect(centerX - roadWidth/2, 0, roadWidth, canvas.height);

      ctx.fillStyle = '#7f8c8d';
      ctx.fillRect(
        centerX - crossSize / 2,
        centerY - crossSize / 2,
        crossSize,
        crossSize
      );

      ctx.strokeStyle = '#ecf0f1';
      ctx.lineWidth = 1;
      ctx.setLineDash([5, 10]);

      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(canvas.width, centerY);
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(centerX, 0);
      ctx.lineTo(centerX, canvas.height);
      ctx.stroke();

      ctx.setLineDash([]);
    }

    // ========== ОТРИСОВКА МАШИН ==========
    vehicles.forEach(vehicle => {
      const { x, y, color, speed, waiting_time: waitingTime } = vehicle;

      // Прямое масштабирование координат
      const screenX = scaleX(x);
      const screenY = scaleY(y);

      // Пропускаем машины за пределами экрана
      if (screenX < -50 || screenX > canvas.width + 50 ||
          screenY < -50 || screenY > canvas.height + 50) {
        return;
      }

      const size = Math.max(5, Math.min(12, speed * 3));
      const opacity = waitingTime > 0 ? 0.7 : 1;

      ctx.save();
      ctx.globalAlpha = opacity;
      ctx.fillStyle = color;

      ctx.beginPath();
      ctx.arc(screenX, screenY, size, 0, Math.PI * 2);
      ctx.fill();

      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();

      if (speed > 0) {
        ctx.fillStyle = '#fff';
        ctx.font = '10px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(speed.toFixed(1), screenX, screenY + size + 12);
      }

      ctx.restore();
    });

    // ========== ОТРИСОВКА СВЕТОФОРОВ ==========
    trafficLights.forEach(light => {
      const { x, y, state, direction, queue_length: queueLength } = light;

      const screenX = scaleX(x);
      const screenY = scaleY(y);

      if (screenX < -50 || screenX > canvas.width + 50 ||
          screenY < -50 || screenY > canvas.height + 50) {
        return;
      }

      const stateColors = {
        RED: '#ff4444',
        YELLOW: '#ffaa00',
        GREEN: '#44ff44',
      };

      const width = direction === 'horizontal' ? 30 : 12;
      const height = direction === 'horizontal' ? 12 : 30;

      ctx.fillStyle = stateColors[state] || '#666';
      ctx.fillRect(
        screenX - width / 2,
        screenY - height / 2,
        width,
        height
      );

      ctx.strokeStyle = '#333';
      ctx.lineWidth = 3;
      ctx.strokeRect(
        screenX - width / 2,
        screenY - height / 2,
        width,
        height
      );

      if (queueLength > 0) {
        ctx.fillStyle = 'rgba(255, 100, 100, 0.9)';
        ctx.beginPath();
        ctx.arc(screenX, screenY - 25, 14, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#fff';
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(queueLength.toString(), screenX, screenY - 25);
      }

      if (state === 'YELLOW') {
        ctx.save();
        ctx.globalAlpha = 0.5 + 0.5 * Math.sin(Date.now() / 500);
        ctx.fillStyle = '#fff';
        ctx.fillRect(
          screenX - width / 2 + 3,
          screenY - height / 2 + 3,
          width - 6,
          height - 6
        );
        ctx.restore();
      }
    });

  }, [vehicles, trafficLights, network, gridWidth, gridHeight, isRunning, roadConfig, networkType]);

  const handleCanvasClick = (e) => {
    if (!canvasRef.current || !onCanvasClick) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const canvas = canvasRef.current;

    const simX = (x / canvas.width) * gridWidth;
    const simY = (y / canvas.height) * gridHeight;

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
        {networkType === 'grid' && network && network.intersections && (
          <div>Intersections: {network.intersections.length}</div>
        )}
      </div>

      {/* Отладочная панель - показывает координаты машин */}
      <div
        style={{
          position: 'absolute',
          bottom: '10px',
          right: '10px',
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          color: 'white',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '10px',
          fontFamily: 'monospace',
          zIndex: 100,
          maxWidth: '250px',
          maxHeight: '150px',
          overflow: 'auto'
        }}
      >
        <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>Vehicles:</div>
        {vehicles.length === 0 && <div>No vehicles</div>}
        {vehicles.slice(0, 5).map(v => (
          <div key={v.id}>#{v.id}: ({Math.round(v.x)}, {Math.round(v.y)}) {v.direction}</div>
        ))}
        {vehicles.length > 5 && <div>...and {vehicles.length - 5} more</div>}
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

      <style>{`
        @keyframes pulse {
          0% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
          100% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
};

SimulationCanvas.propTypes = {
  simulationState: PropTypes.object.isRequired,
  isRunning: PropTypes.bool.isRequired,
  onCanvasClick: PropTypes.func,
};

export default SimulationCanvas;