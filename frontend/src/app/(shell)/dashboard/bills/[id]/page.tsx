import { BillDetail } from "@/components/bills/bill-detail";

export default async function BillCanonicalPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="container mx-auto max-w-4xl">
      <BillDetail id={id} />
    </div>
  );
}
