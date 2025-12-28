import React from 'react';
import PropTypes from 'prop-types';
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, AreaChart, Area
} from 'recharts';

const MetricsDashboard = ({ metrics, historicalMetrics }) => {
  const formatChartData = () => {
    if (!historicalMetrics) return [];

    return historicalMetrics.waiting_time_history?.map((waitingTime, index) => ({
      step: index,
      waitingTime: waitingTime || 0,
      delay: historicalMetrics.delay_history?.[index] || 0,
      throughput: historicalMetrics.throughput_history?.[index] || 0,
      speed: historicalMetrics.speed_history?.[index] || 0,
      vehicles: historicalMetrics.vehicle_count_history?.[index] || 0,
    })) || [];
  };

  const chartData = formatChartData();

  const currentMetrics = metrics || {};

  return (
    <div style={{
      backgroundColor: 'white',
      borderRadius: '8px',
      padding: '20px',
      boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
      marginTop: '20px',
    }}>
      <h3 style={{ marginBottom: '20px', color: '#2c3e50' }}>
        📊 Metrics Dashboard
      </h3>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '30px',
      }}>
        <MetricCard
          title="Average Waiting Time"
          value={currentMetrics.avg_waiting_time?.toFixed(2) || '0'}
          unit="s"
          color="#e74c3c"
        />
        <MetricCard
          title="Total Delay"
          value={currentMetrics.total_delay?.toFixed(2) || '0'}
          unit="s"
          color="#f39c12"
        />
        <MetricCard
          title="Throughput"
          value={currentMetrics.throughput || '0'}
          unit="vehicles"
          color="#27ae60"
        />
        <MetricCard
          title="Average Speed"
          value={currentMetrics.avg_speed?.toFixed(2) || '0'}
          unit="units/s"
          color="#3498db"
        />
        <MetricCard
          title="Active Vehicles"
          value={currentMetrics.total_vehicles || '0'}
          unit=""
          color="#9b59b6"
        />
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
        gap: '20px',
      }}>
        <ChartContainer title="Waiting Time Over Time">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="waitingTime"
                stroke="#e74c3c"
                fill="#e74c3c"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>

        <ChartContainer title="Total Delay Over Time">
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="delay"
                stroke="#f39c12"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>

        <ChartContainer title="Throughput Over Time">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData.slice(-20)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="throughput" fill="#27ae60" />
            </BarChart>
          </ResponsiveContainer>
        </ChartContainer>

        <ChartContainer title="Average Speed Over Time">
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="speed"
                stroke="#3498db"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>
      </div>
    </div>
  );
};

const MetricCard = ({ title, value, unit, color }) => (
  <div style={{
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    padding: '15px',
    textAlign: 'center',
    borderLeft: `4px solid ${color}`,
  }}>
    <div style={{
      fontSize: '12px',
      color: '#7f8c8d',
      marginBottom: '5px',
      fontWeight: '600',
    }}>
      {title}
    </div>
    <div style={{
      fontSize: '24px',
      fontWeight: 'bold',
      color: color,
    }}>
      {value}
      <span style={{ fontSize: '14px', color: '#95a5a6', marginLeft: '4px' }}>
        {unit}
      </span>
    </div>
  </div>
);

const ChartContainer = ({ title, children }) => (
  <div style={{
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    padding: '15px',
  }}>
    <div style={{
      fontSize: '14px',
      fontWeight: '600',
      color: '#2c3e50',
      marginBottom: '10px',
    }}>
      {title}
    </div>
    {children}
  </div>
);

MetricsDashboard.propTypes = {
  metrics: PropTypes.object,
  historicalMetrics: PropTypes.object,
};

MetricCard.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
  unit: PropTypes.string.isRequired,
  color: PropTypes.string.isRequired,
};

ChartContainer.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
};

export default MetricsDashboard;