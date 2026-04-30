const { RuleTester } = require("eslint");
const rule = require("../rules/no-h-screen");

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } },
  },
});

ruleTester.run("no-h-screen", rule, {
  valid: [
    { code: `<div className="min-h-dvh" />` },
    { code: `<div className="h-[200px]" />` },
    { code: `<div className="h-screen-override-custom" />` }, // not exact utility
  ],
  invalid: [
    { code: `<div className="h-screen" />`, errors: [{ messageId: "hScreen" }] },
    { code: `<div className="p-2 h-screen flex" />`, errors: [{ messageId: "hScreen" }] },
    { code: `const c = "md:h-screen"`, errors: [{ messageId: "hScreen" }] },
  ],
});
console.log("no-h-screen PASS");
