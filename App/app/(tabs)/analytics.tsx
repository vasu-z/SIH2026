import React, { useEffect, useState } from 'react';
import { StyleSheet, ScrollView, View, ActivityIndicator, RefreshControl, Dimensions } from 'react-native';
import { LineChart, BarChart } from 'react-native-chart-kit';
import axios from 'axios';
import { Ionicons } from '@expo/vector-icons';

import ParallaxScrollView from '@/components/ParallaxScrollView';
import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';
// No need to import useColorScheme as we're using light mode only

const API_URL = 'http://127.0.0.1:8000/api/water-quality/';

interface WaterQualityData {
  id: number;
  date: string;
  water_level_m: number;
  temperature_c: number;
  rainfall_mm: number;
  ph: string;
  dissolved_oxygen_mg_l: number;
}

export default function AnalyticsScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [waterData, setWaterData] = useState<WaterQualityData[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string>('water_level_m');
  const colorScheme = 'light'; // Always use light mode
  
  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await axios.get(API_URL);
      setWaterData(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load data. Please check your connection.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };
  
  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };
  
  useEffect(() => {
    fetchData();
  }, []);

  // Get recent data for charts
  const recentData = waterData.slice(-30);
  
  // Prepare chart data based on selected metric
  const getMetricData = (metric: string) => {
    // Take every 4th data point to avoid overcrowding labels
    const sampledData = recentData.filter((_, i) => i % 4 === 0);
    
    const colors: Record<string, (opacity: number) => string> = {
      water_level_m: (opacity = 1) => `rgba(65, 105, 225, ${opacity})`, // Blue
      temperature_c: (opacity = 1) => `rgba(231, 76, 60, ${opacity})`, // Red
      rainfall_mm: (opacity = 1) => `rgba(52, 152, 219, ${opacity})`, // Light Blue
      ph: (opacity = 1) => `rgba(46, 204, 113, ${opacity})`, // Green
      dissolved_oxygen_mg_l: (opacity = 1) => `rgba(155, 89, 182, ${opacity})`, // Purple
    };

    const metricLabels: Record<string, string> = {
      water_level_m: "Water Level (m)",
      temperature_c: "Temperature (°C)",
      rainfall_mm: "Rainfall (mm)",
      ph: "pH Level",
      dissolved_oxygen_mg_l: "Dissolved Oxygen (mg/L)",
    };

    return {
      labels: sampledData.map(item => item.date.slice(5)), // Show only month-day
      datasets: [
        {
          data: sampledData.map(item => 
            metric === 'ph' ? parseFloat(item[metric]) : item[metric as keyof WaterQualityData] as number
          ),
          color: colors[metric] || ((opacity = 1) => `rgba(0, 0, 0, ${opacity})`),
          strokeWidth: 2
        }
      ],
      legend: [metricLabels[metric] || metric]
    };
  };

  const chartConfig = {
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    color: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
    strokeWidth: 2,
    barPercentage: 0.5,
    useShadowColorFromDataset: false
  };

  const MetricButton = ({ title, metric }: { title: string; metric: string }) => (
    <ThemedView 
      style={[
        styles.metricButton,
        selectedMetric === metric && styles.selectedMetricButton
      ]}
      onTouchEnd={() => setSelectedMetric(metric)}
    >
      <ThemedText 
        style={[
          styles.metricButtonText,
          selectedMetric === metric && styles.selectedMetricText
        ]}
      >
        {title}
      </ThemedText>
    </ThemedView>
  );

  // Calculate average, min, max for the selected metric
  const getStats = (metric: string) => {
    if (!recentData.length) return { avg: 0, min: 0, max: 0 };
    
    const values = recentData.map(item => 
      metric === 'ph' ? parseFloat(item[metric]) : item[metric as keyof WaterQualityData] as number
    );
    
    return {
      avg: values.reduce((sum, val) => sum + val, 0) / values.length,
      min: Math.min(...values),
      max: Math.max(...values)
    };
  };

  const stats = getStats(selectedMetric);

  // Calculate monthly rainfall totals for bar chart
  const getMonthlyRainfallData = () => {
    const monthlyData: Record<string, number> = {};
    
    waterData.forEach(record => {
      const month = record.date.slice(0, 7); // YYYY-MM format
      if (!monthlyData[month]) {
        monthlyData[month] = 0;
      }
      monthlyData[month] += record.rainfall_mm;
    });
    
    // Get the last 6 months
    const months = Object.keys(monthlyData).sort().slice(-6);
    
    return {
      labels: months.map(m => m.slice(5)), // Just show MM
      datasets: [
        {
          data: months.map(m => monthlyData[m]),
          color: (opacity = 1) => `rgba(52, 152, 219, ${opacity})`,
        }
      ],
      legend: ["Monthly Rainfall (mm)"]
    };
  };

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0000ff" />
        <ThemedText style={styles.loadingText}>Loading data...</ThemedText>
      </View>
    );
  }

  return (
    <ParallaxScrollView
      headerBackgroundColor="#D0D0D0"
      headerTitle="Analytics"
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }>
      
      {error ? (
        <ThemedView style={styles.errorContainer}>
          <Ionicons name="warning" size={32} color="#E74C3C" />
          <ThemedText style={styles.errorText}>{error}</ThemedText>
        </ThemedView>
      ) : (
        <>
          <ThemedView style={styles.titleContainer}>
            <ThemedText type="title">Water Quality Analytics</ThemedText>
          </ThemedView>
          
          <ThemedText style={styles.subtitle}>Parameter Trends (Last 30 Days)</ThemedText>
          
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.metricsScrollContainer}>
            <MetricButton title="Water Level" metric="water_level_m" />
            <MetricButton title="Temperature" metric="temperature_c" />
            <MetricButton title="Rainfall" metric="rainfall_mm" />
            <MetricButton title="pH Level" metric="ph" />
            <MetricButton title="Dissolved Oxygen" metric="dissolved_oxygen_mg_l" />
          </ScrollView>
          
          <ThemedView style={styles.chartContainer}>
            <LineChart
              data={getMetricData(selectedMetric)}
              width={Dimensions.get('window').width - 32}
              height={220}
              chartConfig={chartConfig}
              bezier
              style={styles.chart}
            />
          </ThemedView>
          
          <ThemedView style={styles.statsContainer}>
            <View style={styles.statItem}>
              <ThemedText style={styles.statLabel}>Average</ThemedText>
              <ThemedText style={styles.statValue}>{stats.avg.toFixed(2)}</ThemedText>
            </View>
            <View style={styles.statItem}>
              <ThemedText style={styles.statLabel}>Minimum</ThemedText>
              <ThemedText style={styles.statValue}>{stats.min.toFixed(2)}</ThemedText>
            </View>
            <View style={styles.statItem}>
              <ThemedText style={styles.statLabel}>Maximum</ThemedText>
              <ThemedText style={styles.statValue}>{stats.max.toFixed(2)}</ThemedText>
            </View>
          </ThemedView>
          
          <ThemedText style={styles.subtitle}>Monthly Rainfall</ThemedText>
          
          <ThemedView style={styles.chartContainer}>
            <BarChart
              data={getMonthlyRainfallData()}
              width={Dimensions.get('window').width - 32}
              height={220}
              yAxisLabel=""
              yAxisSuffix="mm"
              chartConfig={chartConfig}
              style={styles.chart}
            />
          </ThemedView>
          
          <ThemedText style={styles.subtitle}>Insights</ThemedText>
          
          <ThemedView style={styles.insightCard}>
            <View style={styles.insightIconContainer}>
              <Ionicons name="analytics" size={24} color="#3498DB" />
            </View>
            <ThemedText style={styles.insightText}>
              The analytics shows a correlation between rainfall patterns and groundwater levels.
              Monitoring these trends helps in sustainable water resource management.
            </ThemedText>
          </ThemedView>
          
          <ThemedView style={styles.insightCard}>
            <View style={styles.insightIconContainer}>
              <Ionicons name="flask" size={24} color="#9B59B6" />
            </View>
            <ThemedText style={styles.insightText}>
              Water quality parameters like pH and dissolved oxygen provide insights into the health
              of groundwater resources and potential contamination issues.
            </ThemedText>
          </ThemedView>
        </>
      )}
    </ParallaxScrollView>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
  },
  errorContainer: {
    padding: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  errorText: {
    marginTop: 10,
    textAlign: 'center',
  },
  titleContainer: {
    marginBottom: 16,
  },
  subtitle: {
    fontSize: 18,
    fontWeight: '600',
    marginTop: 24,
    marginBottom: 12,
    paddingHorizontal: 16,
  },
  metricsScrollContainer: {
    paddingHorizontal: 8,
    marginBottom: 16,
  },
  metricButton: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    marginHorizontal: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.05)',
  },
  selectedMetricButton: {
    backgroundColor: '#3498DB',
  },
  metricButtonText: {
    fontSize: 14,
  },
  selectedMetricText: {
    color: '#FFFFFF',
  },
  chartContainer: {
    borderRadius: 12,
    padding: 8,
    marginHorizontal: 16,
    alignItems: 'center',
  },
  chart: {
    borderRadius: 8,
    padding: 8,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginVertical: 16,
    marginHorizontal: 16,
    padding: 16,
    borderRadius: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statItem: {
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 14,
    opacity: 0.7,
  },
  statValue: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 4,
  },
  insightCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    borderRadius: 12,
    padding: 16,
    marginHorizontal: 16,
    marginVertical: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  insightIconContainer: {
    marginRight: 12,
  },
  insightText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
  },
});
