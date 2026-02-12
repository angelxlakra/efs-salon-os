/**
 * Component for ad-hoc multi-staff assignment (services without templates)
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Users, X, Save } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { StaffContributionCreate } from '@/types/multi-staff';

interface Staff {
  id: string;
  display_name: string;
  is_active: boolean;
}

interface StaffAssignment {
  staff_id: string;
  staff_name: string;
  contribution_percent: number;
}

interface AdHocStaffTeamEditorProps {
  serviceId: string;
  serviceName: string;
  servicePrice: number; // in paise
  currentStaffId?: string | null;
  currentStaffName?: string | null;
  currentContributions?: StaffContributionCreate[];
  availableStaff: Staff[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (contributions: StaffContributionCreate[]) => void;
}

export const AdHocStaffTeamEditor: React.FC<AdHocStaffTeamEditorProps> = ({
  serviceId,
  serviceName,
  servicePrice,
  currentStaffId,
  currentStaffName,
  currentContributions,
  availableStaff,
  open,
  onOpenChange,
  onSave,
}) => {
  const [assignments, setAssignments] = useState<StaffAssignment[]>([]);
  const [totalPercent, setTotalPercent] = useState(0);

  // Initialize assignments when dialog opens
  useEffect(() => {
    if (!open) return;

    if (currentContributions && currentContributions.length > 0) {
      // Load from existing contributions
      const loaded = currentContributions.map((contrib) => {
        const staff = availableStaff.find((s) => s.id === contrib.staff_id);
        return {
          staff_id: contrib.staff_id,
          staff_name: staff?.display_name || 'Unknown',
          contribution_percent: contrib.contribution_percent || 0,
        };
      });
      setAssignments(loaded);
    } else if (currentStaffId && currentStaffName) {
      // Start with current single staff at 100%
      setAssignments([
        {
          staff_id: currentStaffId,
          staff_name: currentStaffName,
          contribution_percent: 100,
        },
      ]);
    } else {
      // Empty state
      setAssignments([]);
    }
  }, [open, currentStaffId, currentStaffName, currentContributions, availableStaff]);

  // Calculate total percentage whenever assignments change
  useEffect(() => {
    const total = assignments.reduce((sum, a) => sum + a.contribution_percent, 0);
    setTotalPercent(total);
  }, [assignments]);

  const handleAddStaff = (staffId: string) => {
    const staff = availableStaff.find((s) => s.id === staffId);
    if (!staff) return;

    // Check if already assigned
    if (assignments.some((a) => a.staff_id === staffId)) {
      return;
    }

    // Calculate equal split percentage
    const newCount = assignments.length + 1;
    const equalPercent = Math.floor(100 / newCount);
    const remainder = 100 - equalPercent * newCount;

    // Update all assignments to equal split
    const newAssignments = assignments.map((a, index) => ({
      ...a,
      contribution_percent: equalPercent + (index === 0 ? remainder : 0),
    }));

    // Add new staff
    newAssignments.push({
      staff_id: staffId,
      staff_name: staff.display_name,
      contribution_percent: equalPercent,
    });

    setAssignments(newAssignments);
  };

  const handleRemoveStaff = (staffId: string) => {
    const filtered = assignments.filter((a) => a.staff_id !== staffId);

    if (filtered.length === 0) {
      setAssignments([]);
      return;
    }

    // Redistribute to equal split
    const equalPercent = Math.floor(100 / filtered.length);
    const remainder = 100 - equalPercent * filtered.length;

    const redistributed = filtered.map((a, index) => ({
      ...a,
      contribution_percent: equalPercent + (index === 0 ? remainder : 0),
    }));

    setAssignments(redistributed);
  };

  const handlePercentChange = (staffId: string, percent: number) => {
    setAssignments(
      assignments.map((a) =>
        a.staff_id === staffId ? { ...a, contribution_percent: percent } : a
      )
    );
  };

  const handleEqualSplit = () => {
    if (assignments.length === 0) return;

    const equalPercent = Math.floor(100 / assignments.length);
    const remainder = 100 - equalPercent * assignments.length;

    const equalized = assignments.map((a, index) => ({
      ...a,
      contribution_percent: equalPercent + (index === 0 ? remainder : 0),
    }));

    setAssignments(equalized);
  };

  const handleSave = () => {
    // Validation
    if (assignments.length === 0) {
      alert('Please assign at least one staff member');
      return;
    }

    if (totalPercent !== 100) {
      alert(`Total percentage must equal 100% (currently ${totalPercent}%)`);
      return;
    }

    // Convert to StaffContributionCreate format
    const contributions: StaffContributionCreate[] = assignments.map((a, index) => ({
      staff_id: a.staff_id,
      role_in_service: `Staff ${index + 1}`, // Generic role name
      sequence_order: index + 1,
      contribution_split_type: 'percentage',
      contribution_percent: a.contribution_percent,
      time_spent_minutes: undefined,
    }));

    onSave(contributions);
    onOpenChange(false);
  };

  const handleCancel = () => {
    onOpenChange(false);
  };

  const availableToAdd = availableStaff.filter(
    (s) => !assignments.some((a) => a.staff_id === s.id)
  );

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toFixed(2)}`;
  };

  const getContributionAmount = (percent: number) => {
    return Math.round((servicePrice * percent) / 100);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Assign Staff Team
          </DialogTitle>
          <DialogDescription>
            Assign multiple staff to <strong>{serviceName}</strong> and set their contribution
            percentages. Total must equal 100%.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Current Assignments */}
          {assignments.length === 0 ? (
            <Alert>
              <AlertDescription>
                No staff assigned yet. Add staff members below to create a team.
              </AlertDescription>
            </Alert>
          ) : (
            <div className="space-y-3">
              {assignments.map((assignment, index) => (
                <div
                  key={assignment.staff_id}
                  className="flex items-center gap-3 p-3 border rounded-lg"
                >
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-600 font-semibold flex-shrink-0">
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium">{assignment.staff_name}</div>
                    <div className="text-sm text-gray-500">
                      {formatPrice(getContributionAmount(assignment.contribution_percent))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      value={assignment.contribution_percent}
                      onChange={(e) =>
                        handlePercentChange(
                          assignment.staff_id,
                          parseInt(e.target.value) || 0
                        )
                      }
                      min="0"
                      max="100"
                      className="w-20 text-right"
                    />
                    <span className="text-sm text-gray-500">%</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-red-600"
                    onClick={() => handleRemoveStaff(assignment.staff_id)}
                    disabled={assignments.length === 1}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* Total Percentage */}
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <span className="font-semibold">Total Contribution</span>
            <div className="flex items-center gap-2">
              <Badge
                variant={totalPercent === 100 ? 'default' : 'destructive'}
                className="text-lg"
              >
                {totalPercent}%
              </Badge>
              {totalPercent !== 100 && (
                <span className="text-sm text-red-600">Must equal 100%</span>
              )}
            </div>
          </div>

          {/* Add Staff */}
          {availableToAdd.length > 0 && (
            <div className="space-y-2">
              <Label>Add Staff Member</Label>
              <Select onValueChange={handleAddStaff}>
                <SelectTrigger>
                  <SelectValue placeholder="Select staff to add..." />
                </SelectTrigger>
                <SelectContent>
                  {availableToAdd.map((staff) => (
                    <SelectItem key={staff.id} value={staff.id}>
                      {staff.display_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Equal Split Button */}
          {assignments.length > 1 && (
            <Button variant="outline" onClick={handleEqualSplit} className="w-full">
              <Users className="h-4 w-4 mr-2" />
              Equal Split ({Math.floor(100 / assignments.length)}% each)
            </Button>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleCancel}>
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={totalPercent !== 100 || assignments.length === 0}>
            <Save className="h-4 w-4 mr-2" />
            Save Team
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
