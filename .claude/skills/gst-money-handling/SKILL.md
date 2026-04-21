---
name: gst-money-handling
description: "Handle GST calculations and money in paise for SalonOS. Use when implementing or reviewing billing, expenses, invoices, or tax logic."
allowed-tools: Read, Grep, Glob, Edit, Write
---

# GST & Money Handling

All money: INTEGER in paise. Convert to/from rupees carefully.
GST: 18% extraction logic, CGST/SGST split.
Use ULID for IDs.
Validate edge cases (rounding, overflows).

Task: Implement or review any billing/expense code.
