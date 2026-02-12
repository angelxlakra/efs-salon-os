"use client"

import { useState, useEffect } from "react"
import { Calendar, DollarSign, TrendingUp, TrendingDown, CheckCircle, AlertCircle, Loader2, Calculator } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"
import { DenominationCounter, DenominationCounts } from "@/components/cash/DenominationCounter"

interface CashDrawerSummary {
  session_id: string | null
  date: string
  is_open: boolean
  opening_float: number
  cash_payments: number
  cash_refunds: number
  expected_cash: number
  closing_counted: number | null
  variance: number | null
}

interface CashDrawerResponse {
  id: string
  opened_by: string
  opened_at: string
  opening_float: number
  closed_by: string | null
  closed_at: string | null
  closing_counted: number | null
  expected_cash: number
  variance: number | null
  opening_denominations: Record<string, number> | null
  closing_denominations: Record<string, number> | null
  cash_taken_out: number | null
  cash_taken_out_reason: string | null
  reopened_at: string | null
  reopened_by: string | null
  reopen_reason: string | null
  notes: string | null
  opening_float_rupees: number
  closing_counted_rupees: number
  variance_rupees: number
}

export default function CashDrawerPage() {
  const [summary, setSummary] = useState<CashDrawerSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [entryMode, setEntryMode] = useState<"quick" | "detailed">("quick")

  // Opening drawer state
  const [openingFloat, setOpeningFloat] = useState<string>("")
  const [openingDenoms, setOpeningDenoms] = useState<DenominationCounts>({
    note_50: 0,
    note_100: 0,
    note_200: 0,
    note_500: 0,
  })

  // Closing drawer state
  const [closingCounted, setClosingCounted] = useState<string>("")
  const [closingDenoms, setClosingDenoms] = useState<DenominationCounts>({
    note_50: 0,
    note_100: 0,
    note_200: 0,
    note_500: 0,
  })
  const [cashTakenOut, setCashTakenOut] = useState<string>("")
  const [cashTakenOutReason, setCashTakenOutReason] = useState<string>("")
  const [notes, setNotes] = useState<string>("")

  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchCurrentDrawer()
  }, [])

  const fetchCurrentDrawer = async () => {
    try {
      setIsLoading(true)
      const { data } = await apiClient.get<CashDrawerSummary>("/cash/current")
      setSummary(data)
    } catch (error: any) {
      console.error("Error fetching cash drawer:", error)
      toast.error(error.response?.data?.detail || "Failed to load cash drawer")
    } finally {
      setIsLoading(false)
    }
  }

  const handleOpenDrawer = async () => {
    try {
      setIsSubmitting(true)

      const payload =
        entryMode === "detailed"
          ? { opening_denominations: openingDenoms }
          : { opening_float: Math.round(parseFloat(openingFloat) * 100) }

      await apiClient.post("/cash/open", payload)
      toast.success("Cash drawer opened successfully")
      await fetchCurrentDrawer()

      // Reset form
      setOpeningFloat("")
      setOpeningDenoms({ note_50: 0, note_100: 0, note_200: 0, note_500: 0 })
    } catch (error: any) {
      console.error("Error opening drawer:", error)
      toast.error(error.response?.data?.detail || "Failed to open cash drawer")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleCloseDrawer = async () => {
    try {
      setIsSubmitting(true)

      const payload = {
        ...(entryMode === "detailed"
          ? { closing_denominations: closingDenoms }
          : { closing_counted: Math.round(parseFloat(closingCounted) * 100) }),
        cash_taken_out: cashTakenOut ? Math.round(parseFloat(cashTakenOut) * 100) : 0,
        cash_taken_out_reason: cashTakenOutReason.trim() || null,
        notes: notes.trim() || null,
      }

      await apiClient.post("/cash/close", payload)
      toast.success("Cash drawer closed successfully")
      await fetchCurrentDrawer()

      // Reset form
      setClosingCounted("")
      setClosingDenoms({ note_50: 0, note_100: 0, note_200: 0, note_500: 0 })
      setCashTakenOut("")
      setCashTakenOutReason("")
      setNotes("")
    } catch (error: any) {
      console.error("Error closing drawer:", error)
      toast.error(error.response?.data?.detail || "Failed to close cash drawer")
    } finally {
      setIsSubmitting(false)
    }
  }

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toLocaleString("en-IN", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`
  }

  const calculateTotal = (denoms: DenominationCounts) => {
    return denoms.note_50 * 50 + denoms.note_100 * 100 + denoms.note_200 * 200 + denoms.note_500 * 500
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading cash drawer...</p>
        </div>
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-2" />
          <p className="text-gray-500">Failed to load cash drawer</p>
        </div>
      </div>
    )
  }

  const isDrawerOpen = summary.is_open
  const variance = summary.variance || 0
  const isShort = variance < 0
  const isExact = variance === 0 && !isDrawerOpen && summary.closing_counted !== null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold">Cash Drawer Management</h1>
        <p className="text-sm text-muted-foreground mt-1">Open and close cash drawer with denomination tracking</p>
      </div>

      {/* Status Card */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <DollarSign className="h-5 w-5 text-gray-500" />
              <div>
                <p className="text-sm font-medium">Drawer Status</p>
                <p className="text-xs text-muted-foreground">
                  {new Date(summary.date).toLocaleDateString("en-IN", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })}
                </p>
              </div>
            </div>
            <Badge className={isDrawerOpen ? "bg-green-500" : "bg-gray-500"}>
              {isDrawerOpen ? "Open" : "Closed"}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Current Drawer Summary (when open) */}
      {isDrawerOpen && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Opening Float</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatPrice(summary.opening_float)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Cash In</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{formatPrice(summary.cash_payments)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Cash Out (Refunds)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{formatPrice(summary.cash_refunds)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">Expected Cash</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{formatPrice(summary.expected_cash)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Open Drawer Form */}
      {!isDrawerOpen && (
        <Card>
          <CardHeader>
            <CardTitle>Open Cash Drawer</CardTitle>
            <CardDescription>Enter the starting cash amount for today</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Entry Mode Toggle */}
            <div className="flex gap-2">
              <Button
                variant={entryMode === "quick" ? "default" : "outline"}
                size="sm"
                onClick={() => setEntryMode("quick")}
                type="button"
              >
                Quick Entry
              </Button>
              <Button
                variant={entryMode === "detailed" ? "default" : "outline"}
                size="sm"
                onClick={() => setEntryMode("detailed")}
                type="button"
              >
                <Calculator className="h-4 w-4 mr-2" />
                Count Denominations
              </Button>
            </div>

            {entryMode === "quick" ? (
              <div className="space-y-2">
                <Label htmlFor="openingFloat">Opening Float (₹)</Label>
                <Input
                  id="openingFloat"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="Enter opening amount"
                  value={openingFloat}
                  onChange={(e) => setOpeningFloat(e.target.value)}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label>Count Note Denominations</Label>
                <DenominationCounter value={openingDenoms} onChange={setOpeningDenoms} />
              </div>
            )}

            <Button onClick={handleOpenDrawer} disabled={isSubmitting || (entryMode === "quick" ? !openingFloat : calculateTotal(openingDenoms) === 0)} className="w-full" size="lg">
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Opening...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Open Drawer
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Close Drawer Form */}
      {isDrawerOpen && (
        <Card>
          <CardHeader>
            <CardTitle>Close Cash Drawer</CardTitle>
            <CardDescription>Count the cash and close the drawer for the day</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Entry Mode Toggle */}
            <div className="flex gap-2">
              <Button
                variant={entryMode === "quick" ? "default" : "outline"}
                size="sm"
                onClick={() => setEntryMode("quick")}
                type="button"
              >
                Quick Entry
              </Button>
              <Button
                variant={entryMode === "detailed" ? "default" : "outline"}
                size="sm"
                onClick={() => setEntryMode("detailed")}
                type="button"
              >
                <Calculator className="h-4 w-4 mr-2" />
                Count Denominations
              </Button>
            </div>

            {entryMode === "quick" ? (
              <div className="space-y-2">
                <Label htmlFor="closingCounted">Actual Cash Counted (₹)</Label>
                <Input
                  id="closingCounted"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="Enter counted amount"
                  value={closingCounted}
                  onChange={(e) => setClosingCounted(e.target.value)}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label>Count Note Denominations</Label>
                <DenominationCounter value={closingDenoms} onChange={setClosingDenoms} />
              </div>
            )}

            {/* Cash Taken Out */}
            <div className="space-y-4 pt-4 border-t">
              <div className="space-y-2">
                <Label htmlFor="cashTakenOut">Cash Taken Out (₹)</Label>
                <Input
                  id="cashTakenOut"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="Amount removed from drawer (optional)"
                  value={cashTakenOut}
                  onChange={(e) => setCashTakenOut(e.target.value)}
                />
              </div>

              {cashTakenOut && parseFloat(cashTakenOut) > 0 && (
                <div className="space-y-2">
                  <Label htmlFor="cashTakenOutReason">Reason for Cash Removal</Label>
                  <Input
                    id="cashTakenOutReason"
                    type="text"
                    placeholder="e.g., Bank deposit, Petty cash"
                    value={cashTakenOutReason}
                    onChange={(e) => setCashTakenOutReason(e.target.value)}
                  />
                </div>
              )}
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label htmlFor="notes">Notes (Optional)</Label>
              <Textarea
                id="notes"
                placeholder="Add any notes about the cash count"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
              />
            </div>

            <Button onClick={handleCloseDrawer} disabled={isSubmitting || (entryMode === "quick" ? !closingCounted : calculateTotal(closingDenoms) === 0)} className="w-full" size="lg">
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Closing...
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Close Drawer
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
