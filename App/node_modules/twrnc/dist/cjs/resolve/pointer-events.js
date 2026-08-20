"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const helpers_1 = require("../helpers");
const ALLOWED_VALUES = [`auto`, `none`, `box-only`, `box-none`];
function pointerEvents(value) {
    if (!ALLOWED_VALUES.includes(value))
        return null;
    return (0, helpers_1.complete)({
        pointerEvents: value,
    });
}
exports.default = pointerEvents;
