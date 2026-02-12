"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Minus, Plus } from "lucide-react"

export interface DenominationCounts {
  note_50: number
  note_100: number
  note_200: number
  note_500: number
}

interface DenominationCounterProps {
  value: DenominationCounts
  onChange: (value: DenominationCounts) => void
  readonly?: boolean
}

const denominations = [
  { value: 500, key: 'note_500' as keyof DenominationCounts, color: 'bg-purple-50 border-purple-200', textColor: 'text-purple-900' },
  { value: 200, key: 'note_200' as keyof DenominationCounts, color: 'bg-yellow-50 border-yellow-200', textColor: 'text-yellow-900' },
  { value: 100, key: 'note_100' as keyof DenominationCounts, color: 'bg-pink-50 border-pink-200', textColor: 'text-pink-900' },
  { value: 50, key: 'note_50' as keyof DenominationCounts, color: 'bg-green-50 border-green-200', textColor: 'text-green-900' },
]

export function DenominationCounter({
  value,
  onChange,
  readonly = false
}: DenominationCounterProps) {
  const total = (
    value.note_50 * 50 +
    value.note_100 * 100 +
    value.note_200 * 200 +
    value.note_500 * 500
  )

  const handleIncrement = (key: keyof DenominationCounts) => {
    onChange({ ...value, [key]: value[key] + 1 })
  }

  const handleDecrement = (key: keyof DenominationCounts) => {
    onChange({ ...value, [key]: Math.max(0, value[key] - 1) })
  }

  const handleChange = (key: keyof DenominationCounts, newValue: string) => {
    const parsed = parseInt(newValue) || 0
    onChange({ ...value, [key]: Math.max(0, parsed) })
  }

  return (
    <div className="space-y-3">
      {denominations.map(({ value: denom, key, color, textColor }) => (
        <div key={denom} className={`flex items-center gap-4 p-3 rounded-lg border ${color}`}>
          <span className={`w-20 text-lg font-bold ${textColor}`}>₹{denom}</span>

          <Button
            variant="outline"
            size="icon"
            onClick={() => handleDecrement(key)}
            disabled={readonly || value[key] === 0}
            type="button"
          >
            <Minus className="h-4 w-4" />
          </Button>

          <Input
            type="number"
            value={value[key]}
            onChange={(e) => handleChange(key, e.target.value)}
            className="w-20 text-center"
            disabled={readonly}
            min="0"
          />

          <Button
            variant="outline"
            size="icon"
            onClick={() => handleIncrement(key)}
            disabled={readonly}
            type="button"
          >
            <Plus className="h-4 w-4" />
          </Button>

          <span className="ml-auto text-sm font-medium">
            = ₹{(value[key] * denom).toLocaleString('en-IN')}
          </span>
        </div>
      ))}

      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg font-bold flex justify-between items-center">
        <span className="text-blue-900">Total</span>
        <span className="text-2xl text-blue-700">₹{total.toLocaleString('en-IN')}</span>
      </div>
    </div>
  )
}
