import React, { useState } from 'react';
import { StyleSheet, View, Switch, ScrollView } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';

interface SettingItemProps {
  icon: string;
  title: string;
  description?: string;
  toggle?: boolean;
  value?: boolean;
  onValueChange?: (value: boolean) => void;
}

export default function SettingsScreen() {
  const [notifications, setNotifications] = useState(true);
  const [locationServices, setLocationServices] = useState(true);
  // Dark mode removed as we're using light mode only
  const [dataSync, setDataSync] = useState(true);

  const SettingItem = ({ icon, title, description, toggle, value, onValueChange }: SettingItemProps) => (
    <ThemedView style={styles.settingItem}>
      <View style={styles.settingIconContainer}>
        <Ionicons name={icon as any} size={24} color="#3498DB" />
      </View>
      <View style={styles.settingContent}>
        <ThemedText type="defaultSemiBold">{title}</ThemedText>
        {description && <ThemedText style={styles.settingDescription}>{description}</ThemedText>}
      </View>
      {toggle && (
        <Switch
          value={value}
          onValueChange={onValueChange}
          trackColor={{ false: "#767577", true: "#81b0ff" }}
          thumbColor={value ? "#3498DB" : "#f4f3f4"}
        />
      )}
    </ThemedView>
  );

  const SettingsSection = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <View style={styles.section}>
      <ThemedText style={styles.sectionTitle}>{title}</ThemedText>
      {children}
    </View>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.contentContainer}>
      <ThemedView style={styles.header}>
        <ThemedText type="title">Settings</ThemedText>
      </ThemedView>

      <SettingsSection title="App Settings">
        <SettingItem
          icon="notifications"
          title="Notifications"
          description="Receive alerts about critical water levels"
          toggle
          value={notifications}
          onValueChange={setNotifications}
        />
        <SettingItem
          icon="location"
          title="Location Services"
          description="Allow app to access your location"
          toggle
          value={locationServices}
          onValueChange={setLocationServices}
        />
        {/* Dark mode setting removed as we're using light mode only */}
        <SettingItem
          icon="sync"
          title="Background Sync"
          description="Sync data when app is in background"
          toggle
          value={dataSync}
          onValueChange={setDataSync}
        />
      </SettingsSection>

      <SettingsSection title="Upcoming Features">
        <SettingItem
          icon="analytics"
          title="Real-time Water Level Fluctuations"
          description="Enhanced analytics for monitoring water levels"
        />
        <SettingItem
          icon="refresh-circle"
          title="Dynamic Recharge Estimation"
          description="Calculate groundwater recharge in real-time"
        />
        <SettingItem
          icon="water"
          title="Groundwater Availability Forecasts"
          description="Predictive analysis of groundwater resources"
        />
        <SettingItem
          icon="clipboard"
          title="Decision Support Tools"
          description="For researchers, planners, and policy makers"
        />
        <SettingItem
          icon="alert-circle"
          title="Critical Level Alerts"
          description="Get notifications for water scarcity risks"
        />
      </SettingsSection>

      <SettingsSection title="About">
        <SettingItem
          icon="information-circle"
          title="About This App"
          description="Smart India Hackathon project for real-time groundwater resource evaluation using DWLR data"
        />
        <SettingItem
          icon="help-circle"
          title="Help & Support"
          description="Get assistance with using the app"
        />
        <SettingItem
          icon="code"
          title="Version"
          description="1.0.0 (Prototype)"
        />
      </SettingsSection>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  contentContainer: {
    paddingBottom: 40,
  },
  header: {
    paddingTop: 60,
    paddingHorizontal: 16,
    paddingBottom: 16,
    marginBottom: 8,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
    marginLeft: 16,
    opacity: 0.6,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    marginVertical: 4,
    marginHorizontal: 16,
    borderRadius: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 3,
    elevation: 2,
  },
  settingIconContainer: {
    marginRight: 12,
  },
  settingContent: {
    flex: 1,
  },
  settingDescription: {
    fontSize: 12,
    marginTop: 2,
    opacity: 0.6,
  },
});
