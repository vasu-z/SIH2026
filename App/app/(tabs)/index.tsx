import React, { useEffect, useState } from 'react';
import { ScrollView, View, ActivityIndicator, RefreshControl } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import { Dimensions } from 'react-native';
import axios from 'axios';
import { Ionicons } from '@expo/vector-icons';
import tw from '@/constants/tailwind';

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

export default function DashboardScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [waterData, setWaterData] = useState<WaterQualityData[]>([]);
  const [error, setError] = useState<string | null>(null);
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

  // Get recent data for overview
  const recentData = waterData.slice(-30);
  
  // Calculate stats
  const currentWaterLevel = recentData.length > 0 ? recentData[recentData.length - 1].water_level_m : 0;
  const averageWaterLevel = recentData.length > 0 
    ? recentData.reduce((sum, record) => sum + record.water_level_m, 0) / recentData.length 
    : 0;
  const currentRainfall = recentData.length > 0 ? recentData[recentData.length - 1].rainfall_mm : 0;
  const currentTemp = recentData.length > 0 ? recentData[recentData.length - 1].temperature_c : 0;
  
  // Prepare chart data
  const waterLevelData = {
    labels: recentData.slice(-7).map(item => item.date.slice(5)), // Show only month-day
    datasets: [
      {
        data: recentData.slice(-7).map(item => item.water_level_m),
        color: (opacity = 1) => `rgba(65, 105, 225, ${opacity})`, // Blue
        strokeWidth: 2
      }
    ],
    legend: ["Water Level (m)"]
  };

  const chartConfig = {
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    color: (opacity = 1) => `rgba(0, 0, 0, ${opacity})`,
    strokeWidth: 2,
    barPercentage: 0.5,
    decimalPlaces: 0,
  };  // Get trend direction
  const getTrend = (current: number, average: number) => {
    const diff = current - average;
    if (diff > 0.1) return "up";
    if (diff < -0.1) return "down";
    return "steady";
  };

  const waterLevelTrend = getTrend(currentWaterLevel, averageWaterLevel);

  // Card for stats
  const StatsCard = ({ title, value, unit, icon, trend = null }: { 
    title: string, 
    value: number, 
    unit: string, 
    icon: any,
    trend?: "up" | "down" | "steady" | null 
  }) => {
    let trendIcon = null;
    let trendColorClass = "";
    
    if (trend === "up") {
      trendIcon = <Ionicons name="arrow-up" size={16} color="#E74C3C" />;
      trendColorClass = "text-red-500";
    } else if (trend === "down") {
      trendIcon = <Ionicons name="arrow-down" size={16} color="#2ECC71" />;
      trendColorClass = "text-green-500";
    } else if (trend === "steady") {
      trendIcon = <Ionicons name="remove" size={16} color="#3498DB" />;
      trendColorClass = "text-blue-500";
    }

    return (
      <ThemedView style={tw`rounded-xl p-4 mx-2 my-1 flex-row items-center shadow-sm bg-white dark:bg-gray-800 min-w-[150px]`}>
        <View style={tw`mr-3`}>
          {icon}
        </View>
        <View>
          <ThemedText type="defaultSemiBold" style={tw`text-sm opacity-80`}>{title}</ThemedText>
          <View style={tw`flex-row items-center`}>
            <ThemedText style={tw`text-base font-bold mt-0.5`}>
              {value.toFixed(2)} {unit}
            </ThemedText>
            {trendIcon && <View style={tw`ml-1.5`}>{trendIcon}</View>}
          </View>
        </View>
      </ThemedView>
    );
  };

  if (loading && !refreshing) {
    return <LoadingIndicator />;
  }

  return (
    <ParallaxScrollView
      headerBackgroundColor="#A1CEDC"
      headerTitle="DWLR Monitoring"
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }
      headerImage={
        <Ionicons name="water" size={120} color="rgba(255,255,255,0.5)" style={tw`absolute bottom-8 right-8`} />
      }>
      
      {error ? (
        <ThemedView style={tw`p-5 items-center justify-center`}>
          <Ionicons name="warning" size={32} color="#E74C3C" />
          <ThemedText style={tw`mt-2.5 text-center`}>{error}</ThemedText>
        </ThemedView>
      ) : (
        <>
          <ThemedView style={tw`mb-4`}>
            <ThemedText type="title">Groundwater Dashboard</ThemedText>
          </ThemedView>
          
          <ThemedText style={tw`text-lg font-semibold mt-6 mb-3 px-4`}>Current Readings</ThemedText>
          
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={tw`px-2`}>
            <StatsCard 
              title="Water Level" 
              value={currentWaterLevel} 
              unit="m" 
              icon={<Ionicons name="water" size={24} color="#3498DB" />}
              trend={waterLevelTrend}
            />
            <StatsCard 
              title="Temperature" 
              value={currentTemp} 
              unit="°C" 
              icon={<Ionicons name="thermometer" size={24} color="#E67E22" />}
            />
            <StatsCard 
              title="Rainfall" 
              value={currentRainfall} 
              unit="mm" 
              icon={<Ionicons name="rainy" size={24} color="#3498DB" />}
            />
          </ScrollView>

          <ThemedText style={tw`text-lg font-semibold mt-6 mb-3 px-4`}>Water Level Trend (Last 7 Days)</ThemedText>
          
          <ThemedView style={tw`rounded-xl p-2 mx-4 items-center`}>
            <LineChart
              data={waterLevelData}
              width={Dimensions.get('window').width - 32}
              height={220}
              chartConfig={chartConfig}
              bezier
              style={tw`rounded-lg p-2`}
            />
          </ThemedView>
          
          <ThemedText style={tw`text-lg font-semibold mt-6 mb-3 px-4`}>Insights</ThemedText>
          
          <ThemedView style={tw`rounded-xl p-4 mx-4 my-2 flex-row items-center shadow-sm bg-white dark:bg-gray-800`}>
            <View style={tw`mr-3`}>
              <Ionicons name="bulb" size={24} color="#F1C40F" />
            </View>
            <ThemedText style={tw`flex-1 text-sm leading-5`}>
              {waterLevelTrend === "up" 
                ? "Water levels are rising. This may be due to recent rainfall or groundwater recharge."
                : waterLevelTrend === "down"
                ? "Water levels are declining. Monitor usage patterns closely."
                : "Water levels are stable at the moment."}
            </ThemedText>
          </ThemedView>
        </>
      )}
    </ParallaxScrollView>
  );
}

// Loading component using Tailwind CSS
const LoadingIndicator = () => (
  <View style={tw`flex-1 justify-center items-center`}>
    <ActivityIndicator size="large" color="#0000ff" />
    <ThemedText style={tw`mt-2.5`}>Loading data...</ThemedText>
  </View>
);

// No styles needed with Tailwind CSS
