import React from 'react';
import PropTypes from 'prop-types';
import {
  LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, AreaChart, Area,
  ComposedChart
} from 'recharts';

const MetricsDashboard = ({ metrics, historicalMetrics }) => {
  const formatChartData = () => {
    if (!historicalMetrics) return [];

    const maxLength = Math.max(
      historicalMetrics.waiting_time_history?.length || 0,
      historicalMetrics.delay_history?.length || 0,
      historicalMetrics.throughput_history?.length || 0,
      historicalMetrics.speed_history?.length || 0,
      historicalMetrics.vehicle_count_history?.length || 0,
      historicalMetrics.stops_history?.length || 0,
      historicalMetrics.co2_history?.length || 0
    );

    return Array.from({ length: maxLength }, (_, index) => ({
      step: index,
      waitingTime: historicalMetrics.waiting_time_history?.[index] || 0,
      delay: historicalMetrics.delay_history?.[index] || 0,
      throughput: historicalMetrics.throughput_history?.[index] || 0,
      speed: historicalMetrics.speed_history?.[index] || 0,
      vehicles: historicalMetrics.vehicle_count_history?.[index] || 0,
      stops: historicalMetrics.stops_history?.[index] || 0,
      co2: historicalMetrics.co2_history?.[index] || 0,
    }));
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

      {/* Traditional Metrics Cards */}
      <h4 style={{ margin: '20px 0 10px', color: '#34495e' }}>🚦 Traffic Metrics</h4>
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
        <MetricCard
          title="Completed Vehicles"
          value={currentMetrics.completed_vehicles || '0'}
          unit=""
          color="#e67e22"
        />
      </div>

      {/* Environmental Metrics Cards */}
      <h4 style={{ margin: '30px 0 10px', color: '#27ae60' }}>🌱 Environmental Impact</h4>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '30px',
      }}>
        <MetricCard
          title="Total Stops"
          value={currentMetrics.total_stops?.toLocaleString() || '0'}
          unit="stops"
          color="#e67e22"
        />
        <MetricCard
          title="Avg Stops/Vehicle"
          value={currentMetrics.avg_stops_per_vehicle?.toString() || '0'}
          unit=""
          color="#d35400"
        />
        <MetricCard
          title="Total CO₂"
          value={currentMetrics.total_co2_g?.toFixed(2) || '0'}
          unit="g"
          color="#2c3e50"
        />
        <MetricCard
          title="Total CO₂"
          value={currentMetrics.total_co2_kg?.toFixed(3) || '0'}
          unit="kg"
          color="#16a085"
        />
        <MetricCard
          title="Avg CO₂/Vehicle"
          value={currentMetrics.avg_co2_per_vehicle_g?.toFixed(2) || '0'}
          unit="g"
          color="#8e44ad"
        />
      </div>

      {/* Charts Grid - All metrics visualized */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '20px',
        marginTop: '30px',
      }}>
        {/* Waiting Time Chart */}
        <ChartContainer title="Average Waiting Time Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" label={{ value: 'Step', position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: 'Seconds', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="waitingTime" stroke="#e74c3c" name="Waiting Time (s)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* Total Delay Chart */}
        <ChartContainer title="Total Delay Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" label={{ value: 'Step', position: 'insideBottom', offset: -5 }} />
              <YAxis label={{ value: 'Seconds', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="delay" stroke="#f39c12" name="Total Delay (s)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* Throughput Chart */}
        <ChartContainer title="Throughput Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData.slice(-30)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="throughput" fill="#27ae60" name="Vehicles Completed" />
            </BarChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* Average Speed Chart */}
        <ChartContainer title="Average Speed Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="speed" stroke="#3498db" name="Speed (units/s)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* Vehicle Count Chart */}
        <ChartContainer title="Active Vehicles Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="vehicles" fill="#9b59b6" stroke="#8e44ad" name="Active Vehicles" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* Total Stops Chart */}
        <ChartContainer title="Total Stops Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="stops" stroke="#e67e22" name="Total Stops" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* CO₂ Emissions Chart */}
        <ChartContainer title="CO₂ Emissions Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="co2" fill="#27ae60" stroke="#2c3e50" name="CO₂ (g)" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>

        {/* Combined Metrics Chart */}
        <ChartContainer title="Combined Environmental Impact">
          <ResponsiveContainer width="100%" height={250}>
            <ComposedChart data={chartData.slice(-50)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
              <XAxis dataKey="step" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="stops" fill="#e67e22" name="Stops" />
              <Line yAxisId="right" type="monotone" dataKey="co2" stroke="#27ae60" name="CO₂ (g)" strokeWidth={2} />
            </ComposedChart>
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
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
  }}>
    <div style={{
      fontSize: '12px',
      color: '#7f8c8d',
      marginBottom: '5px',
      fontWeight: '600',
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    }}>
      {title}
    </div>
    <div style={{
      fontSize: '24px',
      fontWeight: 'bold',
      color: color,
    }}>
      {value}
      <span style={{ fontSize: '14px', color: '#95a5a6', marginLeft: '4px', fontWeight: 'normal' }}>
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
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
  }}>
    <div style={{
      fontSize: '14px',
      fontWeight: '600',
      color: '#2c3e50',
      marginBottom: '15px',
      borderBottom: '2px solid #ecf0f1',
      paddingBottom: '8px',
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