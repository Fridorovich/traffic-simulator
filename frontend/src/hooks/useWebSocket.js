import { useEffect, useRef, useState, useCallback } from 'react';

const useWebSocket = (simId, onMessage, isRunning = false) => {
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const stepIntervalRef = useRef(null);

  const connect = useCallback(() => {
    if (!simId) return;

    if (wsRef.current) {
      wsRef.current.close();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const wsUrl = `${protocol}//${host}:8000/ws/simulation/${simId}`;

    console.log(`Connecting to WebSocket: ${wsUrl}`);

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected successfully');
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'ping' || data.type === 'pong') {
          return;
        }

        onMessage(data);
      } catch (err) {
        console.error('Error parsing WebSocket message:', err, event.data);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('WebSocket connection error');
      setIsConnected(false);
    };

    ws.onclose = (event) => {
      console.log(`WebSocket disconnected. Code: ${event.code}, Reason: ${event.reason}`);
      setIsConnected(false);

      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
        stepIntervalRef.current = null;
      }

      if (simId) {
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect WebSocket...');
          connect();
        }, 2000);
      }
    };

    wsRef.current = ws;
  }, [simId, onMessage]);

  const sendStep = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'step' }));
    }
  }, []);

  useEffect(() => {
    if (isRunning && isConnected) {
      stepIntervalRef.current = setInterval(() => {
        sendStep();
      }, 100);
    } else {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
        stepIntervalRef.current = null;
      }
    }

    return () => {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
      }
    };
  }, [isRunning, isConnected, sendStep]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (stepIntervalRef.current) {
      clearInterval(stepIntervalRef.current);
      stepIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    if (simId) {
      console.log(`Setting up WebSocket for simulation: ${simId}`);
      connect();

      return () => {
        console.log(`Cleaning up WebSocket for simulation: ${simId}`);
        disconnect();
      };
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [simId, connect, disconnect]);

  return {
    isConnected,
    error,
    sendStep,
    disconnect,
    connect: () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      connect();
    },
  };
};

export default useWebSocket;