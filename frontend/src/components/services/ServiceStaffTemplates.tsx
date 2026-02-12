/**
 * Component to display staff role requirements for a multi-person service
 */

import React from 'react';
import { ServiceStaffTemplate } from '@/types/multi-staff';

interface ServiceStaffTemplatesProps {
  templates: ServiceStaffTemplate[];
  showEstimates?: boolean;
  compact?: boolean;
}

export const ServiceStaffTemplatesList: React.FC<ServiceStaffTemplatesProps> = ({
  templates,
  showEstimates = true,
  compact = false
}) => {
  if (!templates || templates.length === 0) {
    return null;
  }

  const sortedTemplates = [...templates].sort(
    (a, b) => a.sequence_order - b.sequence_order
  );

  const getContributionDisplay = (template: ServiceStaffTemplate): string => {
    if (template.contribution_type === 'percentage') {
      return `${template.default_contribution_percent}%`;
    } else if (template.contribution_type === 'fixed') {
      const rupees = (template.default_contribution_fixed || 0) / 100;
      return `₹${rupees.toFixed(2)}`;
    } else {
      return 'Equal Split';
    }
  };

  if (compact) {
    return (
      <div className="text-sm text-gray-600">
        <span className="font-medium">Requires {templates.length} staff:</span>
        {sortedTemplates.map((template, index) => (
          <span key={template.id}>
            {index > 0 && ', '}
            {template.role_name}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <svg
          className="w-5 h-5 text-blue-600"
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
        <h4 className="font-semibold text-blue-900">
          Multi-Staff Service - {templates.length} Roles Required
        </h4>
      </div>

      <div className="space-y-2">
        {sortedTemplates.map((template) => (
          <div
            key={template.id}
            className="bg-white rounded-md p-3 border border-blue-100"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-sm font-medium">
                    {template.sequence_order}
                  </span>
                  <span className="font-medium text-gray-900">
                    {template.role_name}
                  </span>
                  {template.is_required && (
                    <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
                      Required
                    </span>
                  )}
                </div>

                {template.role_description && (
                  <p className="text-sm text-gray-600 mt-1 ml-8">
                    {template.role_description}
                  </p>
                )}
              </div>

              <div className="text-right ml-4">
                <div className="text-sm font-semibold text-blue-700">
                  {getContributionDisplay(template)}
                </div>
                {showEstimates && (
                  <div className="text-xs text-gray-500 mt-1">
                    ~{template.estimated_duration_minutes} min
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-3 text-xs text-gray-600 flex items-center gap-1">
        <svg
          className="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <span>You'll assign specific staff members at checkout</span>
      </div>
    </div>
  );
};

export default ServiceStaffTemplatesList;
