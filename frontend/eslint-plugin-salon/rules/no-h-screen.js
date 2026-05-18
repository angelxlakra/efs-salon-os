"use strict";

// Matches `h-screen` as a standalone utility (possibly prefixed with sm:/md:/lg:/xl:/dark:)
const PATTERN = /(^|\s|:)h-screen(\s|$)/g;

function hasMatch(str) {
  PATTERN.lastIndex = 0;
  return PATTERN.test(str);
}

module.exports = {
  meta: {
    type: "problem",
    messages: {
      hScreen: "`h-screen` is unreliable on mobile (iOS Safari). Use `min-h-dvh` instead.",
    },
    schema: [],
  },
  create(context) {
    return {
      Literal(node) {
        if (typeof node.value === "string" && hasMatch(node.value)) {
          context.report({ node, messageId: "hScreen" });
        }
      },
      TemplateElement(node) {
        if (node.value && node.value.raw && hasMatch(node.value.raw)) {
          context.report({ node, messageId: "hScreen" });
        }
      },
    };
  },
};
