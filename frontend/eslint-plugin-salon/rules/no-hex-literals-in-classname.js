"use strict";

// Detects Tailwind arbitrary-value hex literals: bg-[#fff], text-[#123456], border-[#aaa]
const PATTERN = /\b[a-z-]+\-\[#[0-9a-fA-F]{3,8}\]/g;

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
      hexInClassName:
        "Hex literal '{{match}}' in className. Add a token in tokens.css and reference it — raw hex bypasses light/dark theming.",
    },
    schema: [],
  },
  create(context) {
    function check(node, text) {
      for (const match of findMatches(text)) {
        context.report({ node, messageId: "hexInClassName", data: { match } });
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
