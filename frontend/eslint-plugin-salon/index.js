"use strict";

module.exports = {
  rules: {
    "no-raw-grays": require("./rules/no-raw-grays"),
    "no-hex-literals-in-classname": require("./rules/no-hex-literals-in-classname"),
    "no-h-screen": require("./rules/no-h-screen"),
    "no-list-owned-detail-state": require("./rules/no-list-owned-detail-state"),
  },
};
