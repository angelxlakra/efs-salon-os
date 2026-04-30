const { RuleTester } = require("eslint");
const rule = require("../rules/no-hex-literals-in-classname");

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } },
  },
});

ruleTester.run("no-hex-literals-in-classname", rule, {
  valid: [
    { code: `<div className="bg-accent" />` },
    { code: `const c = "text-text-primary"` },
    { code: `const s = { color: "#111" }` }, // inline style, not className — allowed (not flagged by this rule)
  ],
  invalid: [
    {
      code: `<div className="bg-[#fff]" />`,
      errors: [{ messageId: "hexInClassName" }],
    },
    {
      code: `const c = \`text-[#123abc] \${x}\``,
      errors: [{ messageId: "hexInClassName" }],
    },
  ],
});
console.log("no-hex-literals-in-classname PASS");
