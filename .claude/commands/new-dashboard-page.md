---
description: "Create a new dashboard page with architecture planning, responsive layout, and review. Pass the page name as an argument."
argument-hint: "[page-name]"
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# New Dashboard Page: $ARGUMENTS

Create a new SalonOS dashboard page following the full workflow:

1. **Plan**: Use the architect agent to design the page structure, data requirements, and component breakdown.
2. **Implement**: Build the page using the dashboard-component skill patterns — Next.js App Router, shadcn/ui, mobile-first Tailwind, role-based visibility.
3. **Responsive**: Ensure the layout works on tablets (POS) and mobile. No horizontal scroll, proper breakpoints.
4. **Review**: Run the review-and-test pipeline to validate quality, security, and test coverage.