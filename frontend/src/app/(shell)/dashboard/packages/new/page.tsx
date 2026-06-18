"use client";
import { PackageBuilder } from "@/components/packages/PackageBuilder";

export default function NewPackagePage() {
  // The builder owns its own save/publish lifecycle (it tracks the created id
  // internally and navigates to POS on publish), so no onSaved handoff here.
  return <PackageBuilder />;
}
