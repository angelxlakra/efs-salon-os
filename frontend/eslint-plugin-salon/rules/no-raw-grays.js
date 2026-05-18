"use strict";

const BANNED_FAMILIES = ["gray", "zinc", "slate", "stone", "neutral"];
// Matches tokens like `text-gray-500`, `bg-zinc-900/50`, `border-slate-200`
const PATTERN = new RegExp(
  `\\b(text|bg|border|ring|outline|decoration|divide|fill|stroke|placeholder)-(${BANNED_FAMILIES.join("|")})-\\d+`,
  "g"
);

function* findMatches(str) {
  let m;
  PATTERN.lastIndex = 0;
  while ((m = PATTERN.exec(str))) {
    yield m[0];
  }
}

module.exports = {
  meta: {
    type: "problem",
    messages: {
      rawGray:
        "Raw Tailwind gray utility '{{match}}'. Use a semantic token (text-muted, bg-surface-card, border-default) — grays must go through tokens.",
    },
    schema: [],
  },
  create(context) {
    function check(node, text) {
      for (const match of findMatches(text)) {
        context.report({ node, messageId: "rawGray", data: { match } });
      }
    }
    return {
      Literal(node) {
        if (typeof node.value === "string") check(node, node.value);
      },
      TemplateElement(node) {
        if (node.value && node.value.raw) check(node, node.value.raw);
      },
    };
  },
};
