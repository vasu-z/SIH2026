import React, { useEffect, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import tw from '@/constants/tailwind';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';
import { apiGet, StationSummary, SystemOverview } from '@/lib/api';

type StationStatus = 'normal' | 'warning' | 'critical';

type StationSummaryResponse = {
  station_count: number;
  stations: StationSummary[];
};

function getStationStatus(station: StationSummary): StationStatus {
  if (station.latest_level >= 15 || station.trend_7d > 0.5) return 'critical';
  if (station.latest_level >= 11 || station.trend_7d > 0.2) return 'warning';
  return 'normal';
}

export default function MapScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stations, setStations] = useState<StationSummary[]>([]);
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStations = async () => {
    try {
      setLoading(true);
      const [summary, systemOverview] = await Promise.all([
        apiGet<StationSummaryResponse>('/data/stations/summary/'),
        apiGet<SystemOverview>('/system/overview/'),
      ]);
      setStations(summary.stations);
      setOverview(systemOverview);
      setError(null);
    } catch (err) {
      console.error('Error fetching stations:', err);
      setError('Failed to load station data from backend.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStations();
  }, []);

  return (
    <ScrollView
      style={tw`flex-1 pt-14`}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchStations(); }} />}>
      <ThemedView style={tw`px-4 pb-4`}>
        <ThemedText type="title">DWLR Station Network</ThemedText>
        <ThemedText style={tw`mt-1 opacity-70`}>
          {overview?.data_mode || 'Backend'} · {stations.length} stations · {overview?.database.total_records ?? 0} records
        </ThemedText>
      </ThemedView>

      <View style={tw`mx-4 my-4 rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800`}>
        <View style={tw`p-4`}>
          <View style={tw`flex-row items-center mb-3`}>
            <Ionicons name="map" size={28} color="#3498DB" />
            <ThemedText type="defaultSemiBold" style={tw`ml-2`}>
              API-backed station locations
            </ThemedText>
          </View>

          {loading && !refreshing ? (
            <View style={tw`py-8 justify-center items-center`}>
              <ActivityIndicator size="large" color="#3498DB" />
              <ThemedText style={tw`mt-2`}>Loading backend stations...</ThemedText>
            </View>
          ) : error ? (
            <ThemedView style={tw`p-4 items-center`}>
              <Ionicons name="warning" size={28} color="#E74C3C" />
              <ThemedText style={tw`mt-2 text-center`}>{error}</ThemedText>
            </ThemedView>
          ) : (
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {stations.map(station => {
                const status = getStationStatus(station);
                return (
                  <View
                    key={station.station_id}
                    style={tw`bg-white dark:bg-gray-700 p-3 mx-2 rounded-lg shadow-sm border-l-4 ${
                      status === 'critical' ? 'border-red-500' :
                      status === 'warning' ? 'border-yellow-500' :
                      'border-blue-500'
                    }`}>
                    <ThemedText style={tw`font-bold`}>{station.station_id}</ThemedText>
                    <ThemedText style={tw`mt-1`}>Latest Level: {station.latest_level?.toFixed(2)}m</ThemedText>
                    <ThemedText style={tw`mt-1`}>7D Trend: {station.trend_7d > 0 ? '+' : ''}{station.trend_7d}m</ThemedText>
                    <ThemedText style={tw`capitalize mt-1 ${
                      status === 'critical' ? 'text-red-600' :
                      status === 'warning' ? 'text-yellow-600' :
                      'text-blue-600'
                    }`}>
                      Status: {status}
                    </ThemedText>
                    <View style={tw`flex-row items-center mt-2`}>
                      <ThemedText style={tw`text-xs text-gray-500`}>Lat: {station.lat.toFixed(2)}</ThemedText>
                      <ThemedText style={tw`text-xs text-gray-500 ml-2`}>Long: {station.lon.toFixed(2)}</ThemedText>
                    </View>
                    <ThemedText style={tw`text-xs text-gray-500 mt-1`}>Latest: {station.latest_date}</ThemedText>
                  </View>
                );
              })}
            </ScrollView>
          )}
        </View>
      </View>

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
          <Ionicons name="shield-checkmark" size={24} color={overview?.database.live_records ? '#10B981' : '#F59E0B'} />
          <ThemedText type="defaultSemiBold" style={tw`text-base ml-2`}>
            Source Integrity
          </ThemedText>
        </View>
        <ThemedText style={tw`text-sm leading-5`}>
          Live public records: {overview?.database.live_records ?? 0}. Synthetic fallback records: {overview?.database.synthetic_records ?? 0}.
          Sync CGWB public data from the web command center to move this app from demo fallback to public-source mode.
        </ThemedText>
      </ThemedView>
    </ScrollView>
  );
}
