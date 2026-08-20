import type { TwTheme } from '../tw-config';
import type { ParseContext, StyleIR } from '../types';
export declare function scale(value: string, context?: ParseContext, config?: TwTheme['scale']): StyleIR | null;
export declare function rotate(value: string, context?: ParseContext, config?: TwTheme['rotate']): StyleIR | null;
export declare function skew(value: string, context?: ParseContext, config?: TwTheme['skew']): StyleIR | null;
export declare function translate(value: string, context?: ParseContext, config?: TwTheme['translate']): StyleIR | null;
export declare function transformNone(): StyleIR;
