const { RuleTester } = require("eslint");
const rule = require("../rules/no-raw-grays");

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } },
  },
});

ruleTester.run("no-raw-grays", rule, {
  valid: [
    { code: `const c = "text-text-muted bg-surface-card"` },
    { code: `<div className="text-accent" />` },
    { code: `const x = "text-red-500"` }, // red is not a banned family
  ],
  invalid: [
    {
      code: `<div className="text-gray-500" />`,
      errors: [{ messageId: "rawGray" }],
    },
    {
      code: `const c = "bg-zinc-900 p-2"`,
      errors: [{ messageId: "rawGray" }],
    },
    {
      code: `const c = \`border-slate-200 \${flag && "text-neutral-700"}\``,
      errors: [{ messageId: "rawGray" }, { messageId: "rawGray" }],
    },
  ],
});

console.log("no-raw-grays PASS");
