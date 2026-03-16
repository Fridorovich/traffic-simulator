import { useEffect, useRef, useState, useCallback } from 'react';

const useWebSocket = (simId, onMessage, isRunning = false) => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 3;
  const connectionLockRef = useRef(false); // Блокировка для предотвращения множественных соединений

  const disconnect = useCallback(() => {
    console.log('Disconnecting WebSocket...');

    // Очищаем все таймеры
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      // Убираем обработчики чтобы избежать лишних вызовов
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.onopen = null;

      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close(1000, "Component unmount");
      }
      wsRef.current = null;
    }

    setIsConnected(false);
    connectionLockRef.current = false;
  }, []);

  const connect = useCallback(() => {
    // Предотвращаем множественные подключения
    if (connectionLockRef.current) {
      console.log('Connection already in progress, skipping...');
      return;
    }

    if (!simId || !isRunning) {
      disconnect();
      return;
    }

    // Если уже есть соединение, не создаем новое
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    connectionLockRef.current = true;

    // Закрываем предыдущее соединение если есть
    if (wsRef.current) {
      disconnect();
    }

    // Определяем URL для WebSocket
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = '8000';
    const wsUrl = `${protocol}//${host}:${port}/ws/simulation/${simId}`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected successfully');
      setIsConnected(true);
      setError(null);
      reconnectAttemptsRef.current = 0;
      connectionLockRef.current = false;

      // Отправляем ping при подключении
      ws.send(JSON.stringify({ type: 'ping' }));

      // Устанавливаем интервал для отправки ping каждые 30 секунд
      pingIntervalRef.current = setInterval(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          console.log('Sending ping');
          wsRef.current.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'pong') {
          console.log('Received pong');
          return;
        }

        onMessage(data);
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('WebSocket connection error');
      connectionLockRef.current = false;
    };

    ws.onclose = (event) => {
      console.log(`WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`);
      setIsConnected(false);
      connectionLockRef.current = false;

      // Очищаем ping интервал
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      // Пытаемся переподключиться только если симуляция всё ещё запущена
      if (simId && isRunning && reconnectAttemptsRef.current < maxReconnectAttempts) {
        const delay = 5000; // Фиксированная задержка 5 секунд
        console.log(`Attempting to reconnect in ${delay}ms... (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);

        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectAttemptsRef.current += 1;
          connect();
        }, delay);
      }
    };

    wsRef.current = ws;
  }, [simId, onMessage, isRunning, disconnect]);

  // Подключаемся при изменении simId или isRunning
  useEffect(() => {
    if (simId && isRunning) {
      // Небольшая задержка перед подключением
      const timer = setTimeout(() => {
        connect();
      }, 100);

      return () => {
        clearTimeout(timer);
        disconnect();
      };
    } else {
      disconnect();
    }
  }, [simId, isRunning, connect, disconnect]);

  return {
    isConnected,
    error,
    disconnect,
    reconnect: () => {
      reconnectAttemptsRef.current = 0;
      disconnect();
      setTimeout(() => connect(), 100);
    },
  };
};

export default useWebSocket;