/**
 * Component for managing staff role templates for a service
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Plus, Trash2, GripVertical, Save, X, Users } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { ServiceStaffTemplate } from '@/types/multi-staff';

interface ServiceStaffTemplateManagerProps {
  serviceId: string | null;
  serviceName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

interface TemplateFormData {
  id?: string;
  role_name: string;
  role_description: string;
  sequence_order: number;
  contribution_type: 'percentage' | 'fixed' | 'equal';
  default_contribution_percent: number | null;
  default_contribution_fixed: number | null;
  estimated_duration_minutes: number;
  is_required: boolean;
}

const emptyTemplate: TemplateFormData = {
  role_name: '',
  role_description: '',
  sequence_order: 1,
  contribution_type: 'percentage',
  default_contribution_percent: 33,
  default_contribution_fixed: null,
  estimated_duration_minutes: 30,
  is_required: true,
};

export const ServiceStaffTemplateManager: React.FC<ServiceStaffTemplateManagerProps> = ({
  serviceId,
  serviceName,
  open,
  onOpenChange,
  onSuccess,
}) => {
  const [templates, setTemplates] = useState<ServiceStaffTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<TemplateFormData | null>(null);
  const [isAddingNew, setIsAddingNew] = useState(false);

  useEffect(() => {
    if (open && serviceId) {
      fetchTemplates();
    }
  }, [open, serviceId]);

  const fetchTemplates = async () => {
    if (!serviceId) return;

    try {
      setIsLoading(true);
      const { data } = await apiClient.get(`/catalog/services/${serviceId}/staff-templates`);
      setTemplates(data.templates || []);
    } catch (error: any) {
      if (error.response?.status !== 404) {
        console.error('Error fetching templates:', error);
        toast.error('Failed to load staff roles');
      }
      setTemplates([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddNew = () => {
    setEditingTemplate({
      ...emptyTemplate,
      sequence_order: templates.length + 1,
    });
    setIsAddingNew(true);
  };

  const handleEdit = (template: ServiceStaffTemplate) => {
    setEditingTemplate({
      id: template.id,
      role_name: template.role_name,
      role_description: template.role_description || '',
      sequence_order: template.sequence_order,
      contribution_type: template.contribution_type as 'percentage' | 'fixed' | 'equal',
      default_contribution_percent: template.default_contribution_percent ?? null,
      default_contribution_fixed: template.default_contribution_fixed ?? null,
      estimated_duration_minutes: template.estimated_duration_minutes,
      is_required: template.is_required,
    });
    setIsAddingNew(false);
  };

  const handleSave = async () => {
    if (!editingTemplate || !serviceId) return;

    // Validation
    if (!editingTemplate.role_name.trim()) {
      toast.error('Role name is required');
      return;
    }
    if (editingTemplate.estimated_duration_minutes <= 0) {
      toast.error('Duration must be greater than 0');
      return;
    }
    if (
      editingTemplate.contribution_type === 'percentage' &&
      (editingTemplate.default_contribution_percent === null ||
        editingTemplate.default_contribution_percent <= 0 ||
        editingTemplate.default_contribution_percent > 100)
    ) {
      toast.error('Contribution percentage must be between 1 and 100');
      return;
    }
    if (
      editingTemplate.contribution_type === 'fixed' &&
      (editingTemplate.default_contribution_fixed === null ||
        editingTemplate.default_contribution_fixed <= 0)
    ) {
      toast.error('Fixed contribution must be greater than 0');
      return;
    }

    try {
      setIsSaving(true);

      const payload = {
        role_name: editingTemplate.role_name.trim(),
        role_description: editingTemplate.role_description.trim() || null,
        sequence_order: editingTemplate.sequence_order,
        contribution_type: editingTemplate.contribution_type,
        default_contribution_percent:
          editingTemplate.contribution_type === 'percentage'
            ? editingTemplate.default_contribution_percent
            : null,
        default_contribution_fixed:
          editingTemplate.contribution_type === 'fixed'
            ? editingTemplate.default_contribution_fixed
            : null,
        estimated_duration_minutes: editingTemplate.estimated_duration_minutes,
        is_required: editingTemplate.is_required,
      };

      if (isAddingNew) {
        // Create new template
        await apiClient.post(`/catalog/services/${serviceId}/staff-templates`, payload);
        toast.success('Staff role added successfully');
      } else if (editingTemplate.id) {
        // Update existing template
        await apiClient.patch(
          `/catalog/services/${serviceId}/staff-templates/${editingTemplate.id}`,
          payload
        );
        toast.success('Staff role updated successfully');
      }

      setEditingTemplate(null);
      setIsAddingNew(false);
      fetchTemplates();
      onSuccess?.();
    } catch (error: any) {
      console.error('Error saving template:', error);
      toast.error(error.response?.data?.detail || 'Failed to save staff role');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (templateId: string) => {
    if (!serviceId) return;
    if (!confirm('Are you sure you want to delete this staff role?')) return;

    try {
      await apiClient.delete(`/catalog/services/${serviceId}/staff-templates/${templateId}`);
      toast.success('Staff role deleted successfully');
      fetchTemplates();
      onSuccess?.();
    } catch (error: any) {
      console.error('Error deleting template:', error);
      toast.error(error.response?.data?.detail || 'Failed to delete staff role');
    }
  };

  const handleCancel = () => {
    setEditingTemplate(null);
    setIsAddingNew(false);
  };

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toFixed(2)}`;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Configure Staff Roles
          </DialogTitle>
          <DialogDescription>
            Define the staff roles required for <strong>{serviceName}</strong>. Each role will
            be assigned during checkout.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Existing Templates */}
          {isLoading ? (
            <div className="text-center py-8 text-gray-500">Loading roles...</div>
          ) : templates.length === 0 && !editingTemplate ? (
            <div className="text-center py-8 border-2 border-dashed rounded-lg">
              <Users className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 mb-4">No staff roles configured yet</p>
              <p className="text-sm text-gray-400 mb-4">
                This service will use single-staff assignment at checkout.
                <br />
                Add roles to enable multi-staff team assignment.
              </p>
              <Button onClick={handleAddNew}>
                <Plus className="h-4 w-4 mr-2" />
                Add First Role
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
              {templates
                .sort((a, b) => a.sequence_order - b.sequence_order)
                .map((template, index) => (
                  <div
                    key={template.id}
                    className="border rounded-lg p-4 hover:border-gray-400 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-600 font-semibold flex-shrink-0">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <h4 className="font-semibold text-gray-900">{template.role_name}</h4>
                            {template.role_description && (
                              <p className="text-sm text-gray-500 mt-1">
                                {template.role_description}
                              </p>
                            )}
                          </div>
                          <div className="flex gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0"
                              onClick={() => handleEdit(template)}
                            >
                              <GripVertical className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 w-8 p-0 text-red-600"
                              onClick={() => handleDelete(template.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          <Badge variant="secondary">
                            {template.estimated_duration_minutes} min
                          </Badge>
                          {template.contribution_type === 'percentage' && template.default_contribution_percent && (
                            <Badge variant="secondary">
                              {template.default_contribution_percent}% contribution
                            </Badge>
                          )}
                          {template.contribution_type === 'fixed' && template.default_contribution_fixed && (
                            <Badge variant="secondary">
                              {formatPrice(template.default_contribution_fixed)} fixed
                            </Badge>
                          )}
                          {template.contribution_type === 'equal' && (
                            <Badge variant="secondary">Equal split</Badge>
                          )}
                          {template.is_required && (
                            <Badge variant="outline" className="border-orange-500 text-orange-600">
                              Required
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}

          {/* Add New / Edit Form */}
          {editingTemplate && (
            <div className="border-2 border-blue-200 rounded-lg p-4 bg-blue-50/50">
              <h4 className="font-semibold mb-4 text-blue-900">
                {isAddingNew ? 'Add New Role' : 'Edit Role'}
              </h4>
              <div className="grid grid-cols-2 gap-4">
                {/* Role Name */}
                <div className="col-span-2">
                  <Label>Role Name *</Label>
                  <Input
                    value={editingTemplate.role_name}
                    onChange={(e) =>
                      setEditingTemplate({ ...editingTemplate, role_name: e.target.value })
                    }
                    placeholder="e.g., Application Specialist"
                  />
                </div>

                {/* Role Description */}
                <div className="col-span-2">
                  <Label>Description</Label>
                  <Textarea
                    value={editingTemplate.role_description}
                    onChange={(e) =>
                      setEditingTemplate({ ...editingTemplate, role_description: e.target.value })
                    }
                    placeholder="Brief description of this role's responsibilities"
                    rows={2}
                  />
                </div>

                {/* Duration */}
                <div>
                  <Label>Estimated Duration (minutes) *</Label>
                  <Input
                    type="number"
                    value={editingTemplate.estimated_duration_minutes}
                    onChange={(e) =>
                      setEditingTemplate({
                        ...editingTemplate,
                        estimated_duration_minutes: parseInt(e.target.value) || 0,
                      })
                    }
                    min="1"
                  />
                </div>

                {/* Contribution Type */}
                <div>
                  <Label>Contribution Type *</Label>
                  <Select
                    value={editingTemplate.contribution_type}
                    onValueChange={(value: 'percentage' | 'fixed' | 'equal') =>
                      setEditingTemplate({ ...editingTemplate, contribution_type: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="percentage">Percentage</SelectItem>
                      <SelectItem value="fixed">Fixed Amount</SelectItem>
                      <SelectItem value="equal">Equal Split</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Contribution Percentage (if percentage type) */}
                {editingTemplate.contribution_type === 'percentage' && (
                  <div>
                    <Label>Default Contribution % *</Label>
                    <Input
                      type="number"
                      value={editingTemplate.default_contribution_percent || ''}
                      onChange={(e) =>
                        setEditingTemplate({
                          ...editingTemplate,
                          default_contribution_percent: parseInt(e.target.value) || null,
                        })
                      }
                      min="1"
                      max="100"
                    />
                  </div>
                )}

                {/* Contribution Fixed (if fixed type) */}
                {editingTemplate.contribution_type === 'fixed' && (
                  <div>
                    <Label>Fixed Amount (₹) *</Label>
                    <Input
                      type="number"
                      value={
                        editingTemplate.default_contribution_fixed
                          ? editingTemplate.default_contribution_fixed / 100
                          : ''
                      }
                      onChange={(e) =>
                        setEditingTemplate({
                          ...editingTemplate,
                          default_contribution_fixed: Math.round(parseFloat(e.target.value) * 100) || null,
                        })
                      }
                      step="0.01"
                      min="0"
                    />
                  </div>
                )}

                {/* Sequence Order */}
                <div>
                  <Label>Sequence Order</Label>
                  <Input
                    type="number"
                    value={editingTemplate.sequence_order}
                    onChange={(e) =>
                      setEditingTemplate({
                        ...editingTemplate,
                        sequence_order: parseInt(e.target.value) || 1,
                      })
                    }
                    min="1"
                  />
                  <p className="text-xs text-gray-500 mt-1">Order of execution (1, 2, 3...)</p>
                </div>

                {/* Is Required */}
                <div className="flex items-center gap-2 pt-6">
                  <input
                    type="checkbox"
                    id="is_required"
                    checked={editingTemplate.is_required}
                    onChange={(e) =>
                      setEditingTemplate({ ...editingTemplate, is_required: e.target.checked })
                    }
                    className="h-4 w-4"
                  />
                  <Label htmlFor="is_required" className="cursor-pointer">
                    Required (must be assigned at checkout)
                  </Label>
                </div>
              </div>

              <div className="flex gap-2 mt-4">
                <Button onClick={handleSave} disabled={isSaving}>
                  {isSaving ? (
                    <>Saving...</>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save Role
                    </>
                  )}
                </Button>
                <Button variant="outline" onClick={handleCancel}>
                  <X className="h-4 w-4 mr-2" />
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Add New Button (when not editing) */}
          {!editingTemplate && templates.length > 0 && (
            <Button variant="outline" onClick={handleAddNew} className="w-full">
              <Plus className="h-4 w-4 mr-2" />
              Add Another Role
            </Button>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
