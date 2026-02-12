/**
 * Component for assigning staff to service roles at checkout
 */

import React, { useState } from 'react';
import {
  ServiceStaffTemplate,
  StaffContributionCreate,
  StaffAssignment
} from '@/types/multi-staff';

interface Staff {
  id: string;
  display_name: string;
  specialization?: string[]; // Optional for backward compatibility
  is_active: boolean;
}

interface StaffAssignmentSelectorProps {
  serviceId: string;
  serviceName: string;
  servicePrice: number;
  templates: ServiceStaffTemplate[];
  availableStaff: Staff[];
  onAssignmentsChange: (contributions: StaffContributionCreate[]) => void;
  splitType?: 'percentage' | 'hybrid';
}

export const StaffAssignmentSelector: React.FC<StaffAssignmentSelectorProps> = ({
  serviceId,
  serviceName,
  servicePrice,
  templates,
  availableStaff,
  onAssignmentsChange,
  splitType = 'percentage'
}) => {
  const [assignments, setAssignments] = useState<Record<string, StaffAssignment>>({});
  const [trackTime, setTrackTime] = useState(splitType === 'hybrid');

  const sortedTemplates = [...templates].sort(
    (a, b) => a.sequence_order - b.sequence_order
  );

  const handleStaffSelect = (templateId: string, staffId: string) => {
    const newAssignments = {
      ...assignments,
      [templateId]: {
        ...assignments[templateId],
        templateId,
        staffId
      }
    };
    setAssignments(newAssignments);
    updateContributions(newAssignments);
  };

  const handleTimeInput = (templateId: string, minutes: number) => {
    const newAssignments = {
      ...assignments,
      [templateId]: {
        ...assignments[templateId],
        templateId,
        actualTimeMinutes: minutes
      }
    };
    setAssignments(newAssignments);
    updateContributions(newAssignments);
  };

  const handleNotesInput = (templateId: string, notes: string) => {
    const newAssignments = {
      ...assignments,
      [templateId]: {
        ...assignments[templateId],
        templateId,
        notes
      }
    };
    setAssignments(newAssignments);
    updateContributions(newAssignments);
  };

  const updateContributions = (currentAssignments: Record<string, StaffAssignment>) => {
    const contributions: StaffContributionCreate[] = [];

    sortedTemplates.forEach((template) => {
      const assignment = currentAssignments[template.id];
      if (!assignment || !assignment.staffId) {
        return; // Skip if no staff assigned yet
      }

      const contribution: StaffContributionCreate = {
        staff_id: assignment.staffId,
        role_in_service: template.role_name,
        sequence_order: template.sequence_order,
        contribution_split_type: trackTime ? 'hybrid' : 'percentage',
        contribution_percent: template.default_contribution_percent,
        notes: assignment.notes
      };

      if (trackTime && assignment.actualTimeMinutes) {
        contribution.time_spent_minutes = assignment.actualTimeMinutes;
      }

      contributions.push(contribution);
    });

    onAssignmentsChange(contributions);
  };

  const isComplete = sortedTemplates.every((template) => {
    if (!template.is_required) return true;
    return assignments[template.id]?.staffId;
  });

  const calculateEstimatedContribution = (template: ServiceStaffTemplate): number => {
    if (template.contribution_type === 'percentage' && template.default_contribution_percent) {
      return (servicePrice * template.default_contribution_percent) / 100;
    }
    return 0;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{serviceName}</h3>
          <p className="text-sm text-gray-600">
            ₹{(servicePrice / 100).toFixed(2)} • {templates.length} staff required
          </p>
        </div>

        {splitType === 'hybrid' && (
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={trackTime}
              onChange={(e) => setTrackTime(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span>Track actual time</span>
          </label>
        )}
      </div>

      <div className="space-y-4">
        {sortedTemplates.map((template) => {
          const assignment = assignments[template.id];
          const estimatedContribution = calculateEstimatedContribution(template);

          return (
            <div
              key={template.id}
              className="border border-gray-200 rounded-lg p-4"
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-semibold text-sm">
                  {template.sequence_order}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <h4 className="font-medium text-gray-900">
                      {template.role_name}
                    </h4>
                    {template.is_required && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                        Required
                      </span>
                    )}
                  </div>

                  <p className="text-sm text-gray-600 mb-3">
                    {template.role_description || 'No description'}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Staff Selection */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Assign Staff
                      </label>
                      <select
                        value={assignment?.staffId || ''}
                        onChange={(e) => handleStaffSelect(template.id, e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="">Select staff member...</option>
                        {availableStaff.map((staff) => (
                          <option key={staff.id} value={staff.id}>
                            {staff.display_name}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Time Input (if tracking) */}
                    {trackTime && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                          Actual Time (minutes)
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="480"
                          value={assignment?.actualTimeMinutes || template.estimated_duration_minutes}
                          onChange={(e) => handleTimeInput(template.id, parseInt(e.target.value))}
                          placeholder={`Est. ${template.estimated_duration_minutes} min`}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    )}
                  </div>

                  {/* Notes */}
                  {assignment?.staffId && (
                    <div className="mt-3">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Notes (optional)
                      </label>
                      <input
                        type="text"
                        value={assignment?.notes || ''}
                        onChange={(e) => handleNotesInput(template.id, e.target.value)}
                        placeholder="Any special notes for this role..."
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  )}

                  {/* Contribution Estimate */}
                  {assignment?.staffId && estimatedContribution > 0 && (
                    <div className="mt-3 flex items-center gap-2 text-sm">
                      <span className="text-gray-600">Est. contribution:</span>
                      <span className="font-semibold text-green-700">
                        ₹{(estimatedContribution / 100).toFixed(2)}
                      </span>
                      <span className="text-gray-500">
                        ({template.default_contribution_percent}%)
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Completion Status */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        {isComplete ? (
          <div className="flex items-center gap-2 text-green-700">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <span className="font-medium">All required staff assigned</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-amber-700">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <span className="font-medium">
              Please assign all required staff members
            </span>
          </div>
        )}
      </div>

      {trackTime && (
        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-md p-3">
          <div className="flex gap-2">
            <svg
              className="w-5 h-5 text-blue-600 flex-shrink-0"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
            <div className="text-sm text-blue-800">
              <strong>Hybrid Mode:</strong> Contributions will be calculated using
              40% base percentage, 30% time spent, and 30% skill complexity.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StaffAssignmentSelector;
