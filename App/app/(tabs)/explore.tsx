import React, { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Pressable,
  RefreshControl,
  ScrollView,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import tw from '@/constants/tailwind';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';
import {
  API_BASE_URL,
  apiGet,
  apiPost,
  DataExplorerResponse,
  LiveSources,
  MlBriefing,
  MlRegistry,
  MlRunResponse,
  PrototypeShowcase,
  UnifiedDecision,
} from '@/lib/api';

type RunKey = 'ai' | 'ridge' | 'stgnn' | 'trust' | 'unified' | 'sync';

const SELECTED_STATION = 'DWLR-001';

function formatRange(range?: { start?: string | null; end?: string | null }) {
  if (!range?.start || !range?.end) return 'No date range';
  return `${range.start} to ${range.end}`;
}

function SourceBadge({ label, live }: { label: string; live?: boolean }) {
  return (
    <View style={tw`px-2 py-1 rounded-full ${live ? 'bg-green-100' : 'bg-indigo-100'}`}>
      <ThemedText style={tw`text-xs font-bold ${live ? 'text-green-700' : 'text-indigo-700'}`}>
        {label}
      </ThemedText>
    </View>
  );
}

function MetricCard({
  title,
  value,
  detail,
  icon,
  color,
}: {
  title: string;
  value: string;
  detail: string;
  icon: keyof typeof Ionicons.glyphMap;
  color: string;
}) {
  return (
    <ThemedView style={tw`w-52 mr-3 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
      <View style={tw`flex-row items-center justify-between mb-3`}>
        <Ionicons name={icon} size={24} color={color} />
        <ThemedText style={tw`text-xs opacity-60`}>LIVE API</ThemedText>
      </View>
      <ThemedText style={tw`text-xs opacity-70`}>{title}</ThemedText>
      <ThemedText style={tw`text-2xl font-bold mt-1`}>{value}</ThemedText>
      <ThemedText style={tw`text-xs opacity-70 mt-2 leading-4`}>{detail}</ThemedText>
    </ThemedView>
  );
}

function ActionButton({
  title,
  endpoint,
  icon,
  loading,
  onPress,
}: {
  title: string;
  endpoint: string;
  icon: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={loading}
      style={({ pressed }) => [
        tw`mb-3 p-4 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700`,
        pressed ? tw`opacity-70` : null,
        loading ? tw`opacity-60` : null,
      ]}>
      <View style={tw`flex-row items-center`}>
        <View style={tw`h-10 w-10 rounded-lg bg-blue-100 items-center justify-center mr-3`}>
          {loading ? <ActivityIndicator color="#2563EB" /> : <Ionicons name={icon} size={21} color="#2563EB" />}
        </View>
        <View style={tw`flex-1`}>
          <ThemedText type="defaultSemiBold">{title}</ThemedText>
          <ThemedText style={tw`text-xs opacity-60 mt-1`}>{endpoint}</ThemedText>
        </View>
        <Ionicons name="chevron-forward" size={20} color="#94A3B8" />
      </View>
    </Pressable>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={tw`mt-6`}>
      <ThemedText style={tw`text-lg font-bold px-4 mb-3`}>{title}</ThemedText>
      {children}
    </View>
  );
}

export default function ExploreScreen() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [runLoading, setRunLoading] = useState<RunKey | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [sources, setSources] = useState<LiveSources | null>(null);
  const [showcase, setShowcase] = useState<PrototypeShowcase | null>(null);
  const [registry, setRegistry] = useState<MlRegistry | null>(null);
  const [explorer, setExplorer] = useState<DataExplorerResponse | null>(null);
  const [briefing, setBriefing] = useState<MlBriefing | null>(null);
  const [aiRun, setAiRun] = useState<MlRunResponse | null>(null);
  const [ridgeRun, setRidgeRun] = useState<MlRunResponse | null>(null);
  const [stgnnRun, setStgnnRun] = useState<MlRunResponse | null>(null);
  const [trustRun, setTrustRun] = useState<MlRunResponse | null>(null);
  const [unified, setUnified] = useState<UnifiedDecision | null>(null);
  const [syncResult, setSyncResult] = useState<Record<string, unknown> | null>(null);

  const loadBase = async () => {
    try {
      setLoading(true);
      const [sourceData, showcaseData, registryData, explorerData, briefingData] = await Promise.all([
        apiGet<LiveSources>('/data/live-sources/'),
        apiGet<PrototypeShowcase>('/prototype/showcase/'),
        apiGet<MlRegistry>('/ml/registry/'),
        apiGet<DataExplorerResponse>('/data/explorer/?include_synthetic=1&page=1&page_size=8&ordering=-date'),
        apiGet<MlBriefing>(`/ml/briefing/?station_id=${SELECTED_STATION}&horizon=30`),
      ]);
      setSources(sourceData);
      setShowcase(showcaseData);
      setRegistry(registryData);
      setExplorer(explorerData);
      setBriefing(briefingData);
      setError(null);
    } catch (err) {
      console.error('AI lab load failed:', err);
      setError('Backend data load failed. Start Django on 127.0.0.1:8000 and pull to refresh.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadBase();
  }, []);

  const runAction = async (key: RunKey) => {
    try {
      setRunLoading(key);
      if (key === 'ai') {
        setAiRun(await apiGet<MlRunResponse>(`/ml/run/?model=ai_ensemble_forecast&station_id=${SELECTED_STATION}&horizon=30`));
      } else if (key === 'ridge') {
        setRidgeRun(await apiGet<MlRunResponse>(`/ml/run/?model=ridge_forecast&station_id=${SELECTED_STATION}&horizon=30`));
      } else if (key === 'stgnn') {
        setStgnnRun(await apiGet<MlRunResponse>(`/ml/run/?model=st_gnn&station_id=${SELECTED_STATION}&horizon=30`));
      } else if (key === 'trust') {
        setTrustRun(await apiGet<MlRunResponse>(`/ml/run/?model=trust_score&station_id=${SELECTED_STATION}`));
      } else if (key === 'unified') {
        setUnified(await apiGet<UnifiedDecision>('/decision/unified/'));
      } else if (key === 'sync') {
        setSyncResult(await apiPost<Record<string, unknown>>('/data/ingest/cgwb/', { limit: 250, historical_dates: 6 }));
        await loadBase();
      }
      setError(null);
    } catch (err) {
      console.error(`Run ${key} failed:`, err);
      setError(`Action failed: ${key}. Check backend logs or network.`);
    } finally {
      setRunLoading(null);
    }
  };

  const exportUrl = useMemo(() => `${API_BASE_URL}/data/export-csv/?include_synthetic=1`, []);

  if (loading && !refreshing) {
    return (
      <View style={tw`flex-1 items-center justify-center px-6`}>
        <ActivityIndicator size="large" color="#2563EB" />
        <ThemedText style={tw`mt-3 text-center`}>Loading live backend command center...</ThemedText>
      </View>
    );
  }

  const aiInput = aiRun?.result.input_data;

  return (
    <ScrollView
      style={tw`flex-1 pt-14 bg-gray-50 dark:bg-gray-950`}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadBase(); }} />}>
      <ThemedView style={tw`px-4 pb-4 bg-gray-50 dark:bg-gray-950`}>
        <ThemedText type="title">AI + Backend Lab</ThemedText>
        <ThemedText style={tw`mt-1 opacity-70 leading-5`}>
          Every card below is backed by Django APIs, SQLite records, source lineage, and model outputs.
        </ThemedText>
      </ThemedView>

      {error ? (
        <ThemedView style={tw`mx-4 mb-4 p-4 rounded-xl bg-red-50 border border-red-100`}>
          <View style={tw`flex-row items-center`}>
            <Ionicons name="warning" size={22} color="#DC2626" />
            <ThemedText style={tw`ml-2 text-red-700 flex-1`}>{error}</ThemedText>
          </View>
        </ThemedView>
      ) : null}

      <Section title="Data Provenance">
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={tw`px-4`}>
          <MetricCard
            title="CGWB public observations"
            value={`${sources?.live_records ?? showcase?.public_data.record_count ?? 0}`}
            detail={`Official/public cache · ${formatRange(showcase?.public_data.date_range)}`}
            icon="cloud-done"
            color="#16A34A"
          />
          <MetricCard
            title="DWLR model-lab telemetry"
            value={`${sources?.synthetic_records ?? showcase?.model_lab.record_count ?? 0}`}
            detail={`Time-series ML lab · ${formatRange(showcase?.model_lab.date_range)}`}
            icon="server"
            color="#4F46E5"
          />
          <MetricCard
            title="Explorer rows available"
            value={`${explorer?.total_records ?? 0}`}
            detail="/api/data/explorer/?include_synthetic=1"
            icon="file-tray-full"
            color="#0891B2"
          />
        </ScrollView>

        <View style={tw`px-4 mt-4`}>
          <ActionButton
            title="Sync CGWB Public Data"
            endpoint="POST /api/data/ingest/cgwb/"
            icon="sync"
            loading={runLoading === 'sync'}
            onPress={() => runAction('sync')}
          />
          {syncResult ? (
            <ThemedView style={tw`p-3 rounded-lg bg-green-50 border border-green-100`}>
              <ThemedText style={tw`text-sm text-green-800`}>
                Sync response: {String(syncResult.status || syncResult.message || 'completed')}
              </ThemedText>
            </ThemedView>
          ) : null}
        </View>
      </Section>

      <Section title="AI/ML Model Registry">
        <ThemedView style={tw`mx-4 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
          <View style={tw`flex-row items-center justify-between mb-3`}>
            <ThemedText type="defaultSemiBold">{registry?.external_repository.name || 'AI Registry'}</ThemedText>
            <SourceBadge label={registry?.external_repository.available ? 'CLONED' : 'MISSING'} live={registry?.external_repository.available} />
          </View>
          <ThemedText style={tw`text-sm leading-5 opacity-80`}>{registry?.external_repository.role}</ThemedText>
          <ThemedText style={tw`text-xs mt-2 opacity-60`}>
            Notebook: {registry?.external_repository.notebook || 'N/A'} · Data files: {registry?.external_repository.data_file_count ?? 0}
          </ThemedText>
        </ThemedView>

        {(registry?.models || []).map(model => (
          <ThemedView key={model.id} style={tw`mx-4 mt-3 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
            <View style={tw`flex-row justify-between items-start`}>
              <View style={tw`flex-1 pr-3`}>
                <ThemedText type="defaultSemiBold">{model.name}</ThemedText>
                <ThemedText style={tw`text-xs mt-1 opacity-60`}>{model.family}</ThemedText>
              </View>
              <SourceBadge label={model.availability} live={model.availability === 'OPERATIONAL'} />
            </View>
            <ThemedText style={tw`text-sm mt-2 leading-5 opacity-80`}>{model.role}</ThemedText>
          </ThemedView>
        ))}
      </Section>

      <Section title="Live Model Runs">
        <View style={tw`px-4`}>
          <ActionButton
            title="Run AI Ensemble Forecast"
            endpoint={`/api/ml/run/?model=ai_ensemble_forecast&station_id=${SELECTED_STATION}`}
            icon="hardware-chip"
            loading={runLoading === 'ai'}
            onPress={() => runAction('ai')}
          />
          <ActionButton
            title="Run Ridge Forecast"
            endpoint={`/api/ml/run/?model=ridge_forecast&station_id=${SELECTED_STATION}`}
            icon="analytics"
            loading={runLoading === 'ridge'}
            onPress={() => runAction('ridge')}
          />
          <ActionButton
            title="Try ST-GNN Adapter"
            endpoint={`/api/ml/run/?model=st_gnn&station_id=${SELECTED_STATION}`}
            icon="git-network"
            loading={runLoading === 'stgnn'}
            onPress={() => runAction('stgnn')}
          />
          <ActionButton
            title="Run Trust / Anomaly QC"
            endpoint={`/api/ml/run/?model=trust_score&station_id=${SELECTED_STATION}`}
            icon="shield-checkmark"
            loading={runLoading === 'trust'}
            onPress={() => runAction('trust')}
          />
        </View>

        {aiRun ? (
          <ThemedView style={tw`mx-4 mt-2 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
            <View style={tw`flex-row justify-between items-center mb-2`}>
              <ThemedText type="defaultSemiBold">AI Ensemble Result</ThemedText>
              <SourceBadge label={aiRun.result.risk?.label || aiRun.result.status} live={aiRun.result.status === 'VERIFIED'} />
            </View>
            <ThemedText style={tw`text-sm leading-5`}>
              Best model: {aiRun.result.best_model || 'N/A'} · Records used: {aiInput?.records_used ?? 0} · Source: {aiInput?.source || 'N/A'}
            </ThemedText>
            <ThemedText style={tw`text-xs opacity-70 mt-1`}>Date range: {formatRange(aiInput?.date_range)}</ThemedText>
            <ThemedText style={tw`text-xs opacity-70 mt-1`}>
              Features: {(aiInput?.features || []).slice(0, 6).join(', ')}{(aiInput?.features || []).length > 6 ? '...' : ''}
            </ThemedText>
            <View style={tw`h-px bg-gray-200 dark:bg-gray-700 my-3`} />
            {(aiRun.result.leaderboard || []).slice(0, 4).map(item => (
              <ThemedText key={item.model} style={tw`text-xs mb-1 opacity-80`}>
                {item.model}: MAE {item.mae ?? 'N/A'} · RMSE {item.rmse ?? 'N/A'} · R2 {item.r2 ?? 'N/A'}
              </ThemedText>
            ))}
          </ThemedView>
        ) : null}

        {ridgeRun || stgnnRun || trustRun ? (
          <ThemedView style={tw`mx-4 mt-3 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
            {ridgeRun ? <ThemedText style={tw`text-sm mb-2`}>Ridge: {ridgeRun.result.status} · source {ridgeRun.result.input_data?.source}</ThemedText> : null}
            {stgnnRun ? (
              <ThemedText style={tw`text-sm mb-2`}>
                ST-GNN: {stgnnRun.result.status} · fallback {stgnnRun.result.fallback_applied ? 'applied' : 'not needed'}
              </ThemedText>
            ) : null}
            {trustRun ? (
              <ThemedText style={tw`text-sm`}>
                Trust: {trustRun.result.trust_score ?? 'N/A'}/100 · {trustRun.result.classification || trustRun.result.status}
              </ThemedText>
            ) : null}
          </ThemedView>
        ) : null}
      </Section>

      <Section title="AI Briefing + Unified Pipeline">
        {briefing ? (
          <ThemedView style={tw`mx-4 p-4 rounded-xl bg-blue-50 border border-blue-100`}>
            <View style={tw`flex-row items-center mb-2`}>
              <Ionicons name="sparkles" size={22} color="#2563EB" />
              <ThemedText type="defaultSemiBold" style={tw`ml-2 text-blue-900`}>Backend-generated briefing</ThemedText>
            </View>
            <ThemedText style={tw`text-sm leading-5 text-blue-900`}>{briefing.briefing}</ThemedText>
          </ThemedView>
        ) : null}

        <View style={tw`px-4 mt-3`}>
          <ActionButton
            title="Run Full Unified Decision Pipeline"
            endpoint="GET /api/decision/unified/"
            icon="git-branch"
            loading={runLoading === 'unified'}
            onPress={() => runAction('unified')}
          />
        </View>

        {unified ? (
          <ThemedView style={tw`mx-4 p-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm`}>
            <View style={tw`flex-row justify-between items-center mb-2`}>
              <ThemedText type="defaultSemiBold">{unified.pipeline}</ThemedText>
              <SourceBadge label={unified.status} live />
            </View>
            <ThemedText style={tw`text-sm leading-5`}>{unified.executive_summary}</ThemedText>
            <ThemedText style={tw`text-xs opacity-60 mt-2`}>Latency: {unified.latency_seconds}s · endpoint /api/decision/unified/</ThemedText>
          </ThemedView>
        ) : null}
      </Section>

      <Section title="Database Explorer Preview">
        <ThemedView style={tw`mx-4 rounded-xl bg-white dark:bg-gray-800 shadow-sm overflow-hidden`}>
          {(explorer?.records || []).map(record => (
            <View key={record.id} style={tw`p-3 border-b border-gray-100 dark:border-gray-700`}>
              <View style={tw`flex-row justify-between items-center`}>
                <ThemedText type="defaultSemiBold" style={tw`flex-1 pr-2`}>{record.station_id}</ThemedText>
                <SourceBadge label={record.is_live_source ? 'CGWB_PUBLIC_ARCGIS' : 'DWLR_MODEL_LAB'} live={record.is_live_source} />
              </View>
              <ThemedText style={tw`text-xs opacity-70 mt-1`}>
                {record.date} · depth {record.water_level_m}m · {record.source_agency || record.source || 'source recorded'}
              </ThemedText>
            </View>
          ))}
        </ThemedView>
        <View style={tw`px-4 mt-3 pb-10`}>
          <ActionButton
            title="Export Backend CSV"
            endpoint="/api/data/export-csv/?include_synthetic=1"
            icon="download"
            onPress={() => Linking.openURL(exportUrl)}
          />
        </View>
      </Section>
    </ScrollView>
  );
}
