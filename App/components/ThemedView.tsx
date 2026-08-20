import { View, type ViewProps } from 'react-native';

import { useThemeColor } from '@/hooks/useThemeColor';

export type ThemedViewProps = ViewProps & {
  lightColor?: string;
  darkColor?: string;
};

export function ThemedView({ style, lightColor, darkColor, ...otherProps }: ThemedViewProps) {
  // Always use light mode
  const backgroundColor = lightColor || '#FFFFFF'; 

  return <View style={[{ backgroundColor }, style]} {...otherProps} />;
}
