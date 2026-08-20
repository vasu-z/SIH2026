"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.transformNone = exports.translate = exports.skew = exports.rotate = exports.scale = void 0;
const types_1 = require("../types");
const helpers_1 = require("../helpers");
function scale(value, context = {}, config) {
    let scaleAxis = ``;
    value = value.replace(/^(x|y)-/, (_, axis) => {
        scaleAxis = axis.toUpperCase();
        return ``;
    });
    let styleVal = null;
    if (config === null || config === void 0 ? void 0 : config[value]) {
        styleVal = (0, helpers_1.parseStyleVal)(config[value], context);
    }
    else if (isArbitraryValue(value)) {
        // arbitrary value should use the value as is
        // e.g `scale-[1.5]` should be 1.5
        const parsed = (0, helpers_1.parseNumericValue)(value.slice(1, -1));
        styleVal = parsed ? parsed[0] : null;
    }
    else {
        // unconfigged value should divide value by 100
        // e.g `scale-99` should be 0.99
        const parsed = (0, helpers_1.parseNumericValue)(value);
        styleVal = parsed ? parsed[0] / 100 : null;
    }
    return styleVal === null ? null : createStyle(styleVal, `scale`, scaleAxis);
}
exports.scale = scale;
function rotate(value, context = {}, config) {
    let rotateAxis = ``;
    value = value.replace(/^(x|y|z)-/, (_, axis) => {
        rotateAxis = axis.toUpperCase();
        return ``;
    });
    let styleVal = null;
    if (config === null || config === void 0 ? void 0 : config[value]) {
        styleVal = (0, helpers_1.parseStyleVal)(config[value], context);
    }
    else if (isArbitraryValue(value)) {
        styleVal = (0, helpers_1.parseUnconfigged)(value, context);
    }
    else {
        // unconfigged value should should be converted to degrees
        // e.g `rotate-99` should be `99deg`
        const parsed = (0, helpers_1.parseNumericValue)(value);
        styleVal = parsed ? (0, helpers_1.toStyleVal)(parsed[0], types_1.Unit.deg, context) : null;
    }
    return styleVal === null ? null : createStyle(styleVal, `rotate`, rotateAxis);
}
exports.rotate = rotate;
function skew(value, context = {}, config) {
    let skewAxis = ``;
    value = value.replace(/^(x|y)-/, (_, axis) => {
        skewAxis = axis.toUpperCase();
        return ``;
    });
    if (skewAxis === ``) {
        return null;
    }
    let styleVal = null;
    if (config === null || config === void 0 ? void 0 : config[value]) {
        styleVal = (0, helpers_1.parseStyleVal)(config[value], context);
    }
    else if (isArbitraryValue(value)) {
        styleVal = (0, helpers_1.parseUnconfigged)(value, context);
    }
    else {
        // unconfigged value should should be converted to degrees
        // e.g `skew-x-99` should be `99deg`
        const parsed = (0, helpers_1.parseNumericValue)(value);
        styleVal = parsed ? (0, helpers_1.toStyleVal)(parsed[0], types_1.Unit.deg, context) : null;
    }
    return styleVal === null ? null : createStyle(styleVal, `skew`, skewAxis);
}
exports.skew = skew;
function translate(value, context = {}, config) {
    let translateAxis = ``;
    value = value.replace(/^(x|y)-/, (_, axis) => {
        translateAxis = axis.toUpperCase();
        return ``;
    });
    if (translateAxis === ``) {
        return null;
    }
    const configValue = config === null || config === void 0 ? void 0 : config[value];
    const styleVal = configValue
        ? (0, helpers_1.parseStyleVal)(configValue, context)
        : (0, helpers_1.parseUnconfigged)(value, context);
    // support for percentage values in translate was only added in RN 0.75
    // source: https://reactnative.dev/blog/2024/08/12/release-0.75#percentage-values-in-translation
    // since the support of this package starts at RN 0.62.2
    // we need to filter out percentages which are non-numeric values
    return styleVal === null || (0, types_1.isString)(styleVal)
        ? null
        : createStyle(styleVal, `translate`, translateAxis);
}
exports.translate = translate;
function transformNone() {
    return {
        kind: `dependent`,
        complete(style) {
            style.transform = [];
        },
    };
}
exports.transformNone = transformNone;
function createStyle(styleVal, property, axis) {
    return {
        kind: `dependent`,
        complete(style) {
            var _a;
            let transform = (_a = style.transform) !== null && _a !== void 0 ? _a : [];
            const key = `${property}${axis}`;
            if (transform.length > 0) {
                transform = transform.filter((transformItem) => transformItem[key] === undefined);
            }
            transform.push({
                [key]: styleVal,
            });
            style.transform = transform;
        },
    };
}
function isArbitraryValue(value) {
    return value.startsWith(`[`) && value.endsWith(`]`);
}
