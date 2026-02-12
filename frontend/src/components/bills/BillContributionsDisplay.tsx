/**
 * Component to display staff contributions on a bill
 */

import React from 'react';
import { BillItemWithContributions, StaffContributionResponse } from '@/types/multi-staff';

interface BillContributionsDisplayProps {
  billItem: BillItemWithContributions;
  showBreakdown?: boolean;
  compact?: boolean;
}

export const BillContributionsDisplay: React.FC<BillContributionsDisplayProps> = ({
  billItem,
  showBreakdown = true,
  compact = false
}) => {
  if (!billItem.staff_contributions || billItem.staff_contributions.length === 0) {
    // Single-staff service
    return null;
  }

  const sortedContributions = [...billItem.staff_contributions].sort(
    (a, b) => a.sequence_order - b.sequence_order
  );

  // Verify total matches line total (for debugging)
  const totalContribution = sortedContributions.reduce(
    (sum, c) => sum + c.contribution_amount,
    0
  );
  const isAccurate = Math.abs(totalContribution - billItem.line_total) < 10; // Allow 10 paise rounding

  if (compact) {
    return (
      <div className="ml-6 mt-2 space-y-1 text-sm">
        {sortedContributions.map((contrib) => (
          <div key={contrib.id} className="flex justify-between text-gray-600">
            <span>
              {contrib.sequence_order}. {contrib.role_in_service}
            </span>
            <span className="font-medium">
              ₹{(contrib.contribution_amount / 100).toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="ml-6 mt-3 bg-gray-50 rounded-lg p-4 border border-gray-200">
      <div className="flex items-center gap-2 mb-3">
        <svg
          className="w-5 h-5 text-gray-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
        <h4 className="font-semibold text-gray-900">Staff Contributions</h4>
      </div>

      <div className="space-y-3">
        {sortedContributions.map((contrib, index) => (
          <div
            key={contrib.id}
            className={`${
              index !== sortedContributions.length - 1 ? 'pb-3 border-b border-gray-200' : ''
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <span className="flex-shrink-0 w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-semibold text-sm">
                  {contrib.sequence_order}
                </span>

                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900">
                    {contrib.role_in_service}
                  </div>

                  <div className="text-sm text-gray-600 mt-1">
                    {contrib.contribution_split_type === 'hybrid' ? (
                      <span>Hybrid calculation</span>
                    ) : contrib.contribution_split_type === 'percentage' ? (
                      <span>{contrib.contribution_percent}% split</span>
                    ) : (
                      <span>{contrib.contribution_split_type} split</span>
                    )}
                    {contrib.time_spent_minutes && (
                      <span> • {contrib.time_spent_minutes} minutes</span>
                    )}
                  </div>

                  {/* Hybrid Breakdown */}
                  {showBreakdown &&
                    contrib.contribution_split_type === 'hybrid' &&
                    (contrib.base_percent_component ||
                      contrib.time_component ||
                      contrib.skill_component) && (
                      <div className="mt-2 text-xs space-y-1">
                        {contrib.base_percent_component && (
                          <div className="flex justify-between text-gray-600">
                            <span>Base ({contrib.contribution_percent}%):</span>
                            <span>
                              ₹{(contrib.base_percent_component / 100).toFixed(2)}
                            </span>
                          </div>
                        )}
                        {contrib.time_component && (
                          <div className="flex justify-between text-gray-600">
                            <span>Time-based:</span>
                            <span>
                              ₹{(contrib.time_component / 100).toFixed(2)}
                            </span>
                          </div>
                        )}
                        {contrib.skill_component && (
                          <div className="flex justify-between text-gray-600">
                            <span>Skill-based:</span>
                            <span>
                              ₹{(contrib.skill_component / 100).toFixed(2)}
                            </span>
                          </div>
                        )}
                      </div>
                    )}

                  {contrib.notes && (
                    <div className="mt-2 text-xs text-gray-500 italic">
                      "{contrib.notes}"
                    </div>
                  )}
                </div>
              </div>

              <div className="ml-4 text-right">
                <div className="text-lg font-bold text-green-700">
                  ₹{(contrib.contribution_amount / 100).toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Total Verification */}
      <div className="mt-4 pt-3 border-t border-gray-300 flex items-center justify-between">
        <span className="font-semibold text-gray-900">Total</span>
        <div className="text-right">
          <div className="text-lg font-bold text-gray-900">
            ₹{(totalContribution / 100).toFixed(2)}
          </div>
          {!isAccurate && (
            <div className="text-xs text-red-600">
              ⚠ Rounding difference detected
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BillContributionsDisplay;
