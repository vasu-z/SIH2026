import React, { useEffect, useState } from 'react';
import { View, Dimensions, ActivityIndicator, Image, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import tw from '@/constants/tailwind';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';
// No need to import useColorScheme as we're using light mode only

type StationStatus = 'normal' | 'warning' | 'critical';

interface DwlrStation {
  id: number;
  name: string;
  coordinate: {
    latitude: number;
    longitude: number;
  };
  waterLevel: number;
  status: StationStatus;
}

// Sample data for DWLR stations
const DWLR_STATIONS: DwlrStation[] = [
  { 
    id: 1, 
    name: 'Delhi DWLR Station', 
    coordinate: { latitude: 28.7041, longitude: 77.1025 },
    waterLevel: 2.3,
    status: 'normal' 
  },
  { 
    id: 2, 
    name: 'Mumbai DWLR Station', 
    coordinate: { latitude: 19.0760, longitude: 72.8777 },
    waterLevel: 1.8,
    status: 'warning' 
  },
  { 
    id: 3, 
    name: 'Bangalore DWLR Station', 
    coordinate: { latitude: 12.9716, longitude: 77.5946 },
    waterLevel: 1.2,
    status: 'critical' 
  },
  { 
    id: 4, 
    name: 'Chennai DWLR Station', 
    coordinate: { latitude: 13.0827, longitude: 80.2707 },
    waterLevel: 2.1,
    status: 'normal' 
  },
  { 
    id: 5, 
    name: 'Kolkata DWLR Station', 
    coordinate: { latitude: 22.5726, longitude: 88.3639 },
    waterLevel: 2.5,
    status: 'normal' 
  },
];

export default function MapScreen() {
  const [loading, setLoading] = useState(true);
  const colorScheme = 'light'; // Always use light mode
  
  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(false);
    }, 1500);
    
    return () => clearTimeout(timer);
  }, []);
  
  // Get marker color based on status
  const getMarkerColor = (status: StationStatus): string => {
    switch(status) {
      case 'critical':
        return '#e74c3c'; // red
      case 'warning':
        return '#f39c12'; // yellow/orange
      default:
        return '#3498db'; // blue
    }
  };

  return (
    <View style={tw`flex-1 pt-14`}>
      <ThemedView style={tw`px-4 pb-4`}>
        <ThemedText type="title">DWLR Station Map</ThemedText>
        <ThemedText style={tw`mt-1 opacity-70`}>
          Showing 5,260 stations across India
        </ThemedText>
      </ThemedView>

      <View style={tw`h-72 mx-4 my-4 rounded-xl overflow-hidden relative bg-gray-100 dark:bg-gray-800`}>
        {/* Simplified map placeholder */}
        <View style={tw`flex-1 justify-center items-center`}>
          <Ionicons name="map" size={60} color="#3498DB" style={tw`opacity-50 mb-4`} />
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={tw`max-h-32`}>
            {DWLR_STATIONS.map(station => (
              <View 
                key={station.id} 
                style={tw`bg-white dark:bg-gray-700 p-3 mx-2 rounded-lg shadow-sm border-l-4 ${
                  station.status === 'critical' ? 'border-red-500' : 
                  station.status === 'warning' ? 'border-yellow-500' : 
                  'border-blue-500'
                }`}
              >
                <ThemedText style={tw`font-bold`}>{station.name}</ThemedText>
                <ThemedText style={tw`mt-1`}>Water Level: {station.waterLevel}m</ThemedText>
                <ThemedText style={tw`capitalize mt-1 ${
                  station.status === 'critical' ? 'text-red-600' : 
                  station.status === 'warning' ? 'text-yellow-600' : 
                  'text-blue-600'
                }`}>
                  Status: {station.status}
                </ThemedText>
                <View style={tw`flex-row items-center mt-2`}>
                  <ThemedText style={tw`text-xs text-gray-500`}>
                    Lat: {station.coordinate.latitude.toFixed(2)}
                  </ThemedText>
                  <ThemedText style={tw`text-xs text-gray-500 ml-2`}>
                    Long: {station.coordinate.longitude.toFixed(2)}
                  </ThemedText>
                </View>
              </View>
            ))}
          </ScrollView>
        </View>
        <ThemedText style={tw`absolute bottom-2 left-2 text-xs text-gray-500`}>
          Map view temporarily replaced with station cards
        </ThemedText>
        
        {loading && (
          <View style={tw`absolute inset-0 bg-white/70 justify-center items-center`}>
            <ActivityIndicator size="large" color="#0000ff" />
            <ThemedText style={tw`mt-2`}>Loading map...</ThemedText>
          </View>
        )}
      </View>
      
      {/* Legend */}
      <ThemedView style={tw`mx-4 p-3 rounded-lg flex-row justify-between bg-gray-100 dark:bg-gray-800`}>
        <View style={tw`flex-row items-center`}>
          <View style={tw`h-3 w-3 rounded-full bg-blue-500 mr-1`} />
          <ThemedText style={tw`text-xs`}>Normal</ThemedText>
        </View>
        <View style={tw`flex-row items-center`}>
          <View style={tw`h-3 w-3 rounded-full bg-yellow-500 mr-1`} />
          <ThemedText style={tw`text-xs`}>Warning</ThemedText>
        </View>
        <View style={tw`flex-row items-center`}>
          <View style={tw`h-3 w-3 rounded-full bg-red-500 mr-1`} />
          <ThemedText style={tw`text-xs`}>Critical</ThemedText>
        </View>
      </ThemedView>

      <ThemedView style={tw`m-4 p-4 rounded-xl shadow-sm bg-white dark:bg-gray-800`}>
        <View style={tw`flex-row items-center mb-3`}>
          <Ionicons name="information-circle" size={24} color="#3498DB" />
          <ThemedText type="defaultSemiBold" style={tw`text-base ml-2`}>
            About DWLR Stations
          </ThemedText>
        </View>
        <ThemedText style={tw`text-sm leading-5 mb-2`}>
          The Digital Water Level Recorders (DWLRs) provide high-frequency water level data across India.
          These 5,260 stations help monitor groundwater levels and analyze recharge patterns.
        </ThemedText>
        <ThemedText style={tw`text-sm leading-5 italic opacity-70 mt-2`}>
          Note: This is a prototype visualization. In the production app, real-time station data
          will be displayed with accurate geolocation and detailed water metrics.
        </ThemedText>
      </ThemedView>
    </View>
  );
}
