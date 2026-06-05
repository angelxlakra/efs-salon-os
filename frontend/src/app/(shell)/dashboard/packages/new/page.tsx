"use client";
import { useRouter } from "next/navigation";
import { PackageBuilder } from "@/components/packages/PackageBuilder";

export default function NewPackagePage() {
  const router = useRouter();
  return (
    <PackageBuilder onSaved={(id) => router.push(`/dashboard/packages/${id}`)} />
  );
}
