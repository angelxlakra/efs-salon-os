const { RuleTester } = require("eslint");
const rule = require("../rules/no-list-owned-detail-state");

const ruleTester = new RuleTester({
  languageOptions: {
    parserOptions: { ecmaVersion: 2022, sourceType: "module", ecmaFeatures: { jsx: true } },
  },
});

ruleTester.run("no-list-owned-detail-state", rule, {
  valid: [
    {
      // Detail dialog on a non-list file — allowed
      filename: "src/components/bills/bill-details-dialog.tsx",
      code: `
        import { Dialog } from "@/components/ui/dialog";
        export function BillDetailsDialog() { return null; }
      `,
    },
    {
      // List page without detail dialog import — allowed
      filename: "src/app/dashboard/bills/page.tsx",
      code: `
        import { useState } from "react";
        export default function Page() {
          const [x, setX] = useState(null);
          return null;
        }
      `,
    },
  ],
  invalid: [
    {
      filename: "src/app/dashboard/bills/page.tsx",
      code: `
        import { useState } from "react";
        import { BillDetailsDialog } from "@/components/bills/bill-details-dialog";
        export default function Page() {
          const [selectedBillId, setSelectedBillId] = useState(null);
          return <BillDetailsDialog billId={selectedBillId} />;
        }
      `,
      errors: [{ messageId: "listOwnsDetail" }],
    },
  ],
});
console.log("no-list-owned-detail-state PASS");
