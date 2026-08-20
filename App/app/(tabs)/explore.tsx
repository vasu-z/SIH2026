import React, { useEffect, useState } from 'react';
import { ActivityIndicator, RefreshControl, ScrollView, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import tw from '@/constants/tailwind';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';
import { apiGet, PrototypeShowcase } from '@/lib/api';

export default function ExploreScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showcase, setShowcase] = useState<PrototypeShowcase | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDecisionData = async () => {
    try {
      setLoading(true);
      const showcaseData = await apiGet<PrototypeShowcase>('/prototype/showcase/');
      setShowcase(showcaseData);
      setError(null);
    } catch (err) {
      console.error('Error fetching decision data:', err);
      setError('Failed to load decision engines from backend.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDecisionData();
  }, []);

  return (
    <ScrollView
      style={tw`flex-1 pt-14`}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchDecisionData(); }} />}>
      <ThemedView style={tw`px-4 pb-4`}>
        <ThemedText type="title">Decision Intelligence</ThemedText>
        <ThemedText style={tw`mt-1 opacity-70`}>
          Live backend priority and incident engines
        </ThemedText>
      </ThemedView>

      {loading && !refreshing ? (
        <View style={tw`py-10 items-center`}>
          <ActivityIndicator size="large" color="#3498DB" />
          <ThemedText style={tw`mt-2`}>Running decision engines...</ThemedText>
        </View>
      ) : error ? (
        <ThemedView style={tw`m-4 p-4 rounded-xl bg-white dark:bg-gray-800 items-center`}>
          <Ionicons name="warning" size={28} color="#E74C3C" />
          <ThemedText style={tw`mt-2 text-center`}>{error}</ThemedText>
        </ThemedView>
      ) : (
        <>
          <ThemedText style={tw`text-lg font-semibold mt-4 mb-3 px-4`}>Priority Regions</ThemedText>
          {(showcase?.models.priority || []).slice(0, 5).map(region => (
            <ThemedView key={region.region_id} style={tw`mx-4 mb-3 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
              <View style={tw`flex-row justify-between items-center`}>
                <ThemedText type="defaultSemiBold" style={tw`flex-1 pr-3`}>{region.region_name}</ThemedText>
                <ThemedText style={tw`font-bold text-blue-600`}>{region.priority_score}/100</ThemedText>
              </View>
              <ThemedText style={tw`mt-1 text-sm opacity-70`}>
                {region.region_id} · {region.classification} · confidence {Math.round(region.evidence_confidence * 100)}%
              </ThemedText>
            </ThemedView>
          ))}

          <ThemedText style={tw`text-lg font-semibold mt-4 mb-3 px-4`}>Incident Radar</ThemedText>
          {(showcase?.models.incidents || []).length === 0 ? (
            <ThemedView style={tw`mx-4 mb-3 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
              <ThemedText style={tw`text-sm opacity-70`}>No active regional incidents detected by the backend.</ThemedText>
            </ThemedView>
          ) : (showcase?.models.incidents || []).slice(0, 5).map(incident => (
            <ThemedView key={incident.incident_id} style={tw`mx-4 mb-3 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
              <View style={tw`flex-row justify-between items-center`}>
                <ThemedText type="defaultSemiBold">{incident.incident_id}</ThemedText>
                <ThemedText style={tw`font-bold text-red-600`}>{incident.severity}</ThemedText>
              </View>
              <ThemedText style={tw`mt-1 text-sm opacity-70`}>
                {incident.station_count} stations · confidence {Math.round(incident.confidence * 100)}%
              </ThemedText>
              {incident.explanation ? <ThemedText style={tw`mt-2 text-sm`}>{incident.explanation}</ThemedText> : null}
            </ThemedView>
          ))}

          <ThemedText style={tw`text-lg font-semibold mt-4 mb-3 px-4`}>Scenario + Optimizer</ThemedText>
          {showcase && (
            <ThemedView style={tw`mx-4 mb-3 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
              <View style={tw`flex-row items-center mb-2`}>
                <Ionicons name="flask" size={22} color="#6366F1" />
                <ThemedText type="defaultSemiBold" style={tw`ml-2`}>{showcase.models.scenario.engine}</ThemedText>
              </View>
              <ThemedText style={tw`text-sm opacity-80`}>
                Groundwater change: {showcase.models.scenario.difference.groundwater_change}m · Risk change: {showcase.models.scenario.difference.risk_change}
              </ThemedText>
              <View style={tw`h-px bg-gray-200 dark:bg-gray-700 my-3`} />
              <View style={tw`flex-row items-center mb-2`}>
                <Ionicons name="calculator" size={22} color="#10B981" />
                <ThemedText type="defaultSemiBold" style={tw`ml-2`}>{showcase.models.optimizer.engine}</ThemedText>
              </View>
              <ThemedText style={tw`text-sm opacity-80`}>
                Budget used: ₹{(showcase.models.optimizer.budget_used / 100000).toFixed(1)}L · Selected actions: {showcase.models.optimizer.selected_interventions.length}
              </ThemedText>
            </ThemedView>
          )}

          <ThemedText style={tw`text-lg font-semibold mt-4 mb-3 px-4`}>Monitoring Expansion</ThemedText>
          {(showcase?.models.monitoring || []).slice(0, 5).map(item => (
            <ThemedView key={item.location_id} style={tw`mx-4 mb-3 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
              <View style={tw`flex-row justify-between items-center`}>
                <ThemedText type="defaultSemiBold" style={tw`flex-1 pr-3`}>{item.location_id}</ThemedText>
                <ThemedText style={tw`font-bold text-green-600`}>{item.priority_score}</ThemedText>
              </View>
              <ThemedText style={tw`mt-1 text-sm opacity-70`}>
                Rank #{item.rank} · estimated cost ₹{(item.estimated_cost / 100000).toFixed(1)}L
              </ThemedText>
            </ThemedView>
          ))}
        </>
      )}
    </ScrollView>
  );
}
