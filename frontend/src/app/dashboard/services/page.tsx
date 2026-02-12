'use client';

import { useState, useEffect } from 'react';
import { Plus, Loader2, Edit2, Trash2, FolderPlus, Upload, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/auth-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { ServiceDialog } from '@/components/services/service-dialog';
import { CategoryDialog } from '@/components/services/category-dialog';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { ImportDialog } from '@/components/services/import-dialog';
import { ServiceStaffTemplateManager } from '@/components/services/ServiceStaffTemplateManager';

interface ServiceCategory {
  id: string;
  name: string;
  description: string;
  display_order: number;
  is_active: boolean;
}

interface Service {
  id: string;
  category_id: string;
  name: string;
  description: string;
  base_price: number; // in paise
  duration_minutes: number;
  is_active: boolean;
  display_order: number;
}

interface CatalogData {
  categories: ServiceCategory[];
  services: Service[];
}

export default function ServicesPage() {
  const { user } = useAuthStore();
  const canManageServices = user?.role === 'owner' || user?.role === 'receptionist';

  const [catalog, setCatalog] = useState<CatalogData>({ categories: [], services: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Dialog states
  const [serviceDialog, setServiceDialog] = useState<{ open: boolean; service: Service | null }>({
    open: false,
    service: null,
  });
  const [categoryDialog, setCategoryDialog] = useState<{ open: boolean; category: ServiceCategory | null }>({
    open: false,
    category: null,
  });
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; type: 'service' | 'category' | null; id: string | null }>({
    open: false,
    type: null,
    id: null,
  });
  const [importDialog, setImportDialog] = useState(false);
  const [templateDialog, setTemplateDialog] = useState<{ open: boolean; service: Service | null }>({
    open: false,
    service: null,
  });

  useEffect(() => {
    fetchCatalog();
  }, []);

  const fetchCatalog = async () => {
    try {
      setIsLoading(true);
      const [categoriesRes, servicesRes] = await Promise.all([
        apiClient.get('/catalog/categories'),
        apiClient.get('/catalog/services'),
      ]);

      setCatalog({
        categories: categoriesRes.data.categories || [],
        services: servicesRes.data.services || [],
      });
    } catch (error: any) {
      toast.error('Failed to load catalog');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteService = async () => {
    if (!deleteDialog.id) return;

    try {
      await apiClient.delete(`/catalog/services/${deleteDialog.id}`);
      toast.success('Service deleted successfully');
      fetchCatalog();
      setDeleteDialog({ open: false, type: null, id: null });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete service');
    }
  };

  const handleDeleteCategory = async () => {
    if (!deleteDialog.id) return;

    try {
      await apiClient.delete(`/catalog/categories/${deleteDialog.id}`);
      toast.success('Category deleted successfully');
      fetchCatalog();
      setDeleteDialog({ open: false, type: null, id: null });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete category');
    }
  };

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toFixed(2)}`;
  };

  const getServicesByCategory = (categoryId: string) => {
    return catalog.services.filter((s) => s.category_id === categoryId);
  };

  const filteredCategories = selectedCategory
    ? catalog.categories.filter((c) => c.id === selectedCategory)
    : catalog.categories;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading services...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Services Management</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage your salon's service catalog and categories
          </p>
        </div>
        {canManageServices && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setImportDialog(true)}
            >
              <Upload className="h-4 w-4 mr-2" />
              Import
            </Button>
            <Button
              variant="outline"
              onClick={() => setCategoryDialog({ open: true, category: null })}
            >
              <FolderPlus className="h-4 w-4 mr-2" />
              New Category
            </Button>
            <Button onClick={() => setServiceDialog({ open: true, service: null })}>
              <Plus className="h-4 w-4 mr-2" />
              New Service
            </Button>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Categories</CardDescription>
            <CardTitle className="text-3xl">{catalog.categories.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Services</CardDescription>
            <CardTitle className="text-3xl">{catalog.services.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Active Services</CardDescription>
            <CardTitle className="text-3xl">
              {catalog.services.filter((s) => s.is_active).length}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Category Filter */}
      {catalog.categories.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          <Button
            variant={selectedCategory === null ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            All Categories
          </Button>
          {catalog.categories.map((category) => (
            <Button
              key={category.id}
              variant={selectedCategory === category.id ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSelectedCategory(category.id)}
            >
              {category.name}
            </Button>
          ))}
        </div>
      )}

      {/* Services by Category */}
      {catalog.categories.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <FolderPlus className="h-12 w-12 text-gray-300 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No categories yet
            </h3>
            <p className="text-gray-500 text-center mb-4">
              Create your first service category to get started
            </p>
            {canManageServices && (
              <Button onClick={() => setCategoryDialog({ open: true, category: null })}>
                <FolderPlus className="h-4 w-4 mr-2" />
                Create Category
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {filteredCategories.map((category) => {
            const services = getServicesByCategory(category.id);
            return (
              <Card key={category.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <CardTitle className="text-xl">{category.name}</CardTitle>
                      {!category.is_active && (
                        <Badge variant="secondary">Inactive</Badge>
                      )}
                      <Badge variant="outline">{services.length} services</Badge>
                    </div>
                    {canManageServices && (
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setCategoryDialog({ open: true, category })
                          }
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() =>
                            setDeleteDialog({
                              open: true,
                              type: 'category',
                              id: category.id,
                            })
                          }
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                    )}
                  </div>
                  {category.description && (
                    <CardDescription>{category.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  {services.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      No services in this category yet
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {services.map((service) => (
                        <div
                          key={service.id}
                          className="border rounded-lg p-4 hover:border-gray-400 transition-colors"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <h4 className="font-semibold text-gray-900">
                                {service.name}
                              </h4>
                              {!service.is_active && (
                                <Badge variant="secondary" className="mt-1">
                                  Inactive
                                </Badge>
                              )}
                            </div>
                            {canManageServices && (
                              <div className="flex gap-1">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0"
                                  onClick={() =>
                                    setServiceDialog({ open: true, service })
                                  }
                                >
                                  <Edit2 className="h-3 w-3" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 text-red-600"
                                  onClick={() =>
                                    setDeleteDialog({
                                      open: true,
                                      type: 'service',
                                      id: service.id,
                                    })
                                  }
                                >
                                  <Trash2 className="h-3 w-3" />
                                </Button>
                              </div>
                            )}
                          </div>
                          {service.description && (
                            <p className="text-sm text-gray-500 mb-3">
                              {service.description}
                            </p>
                          )}
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-semibold text-lg text-gray-900">
                              {formatPrice(service.base_price)}
                            </span>
                            <span className="text-gray-500">
                              {service.duration_minutes} min
                            </span>
                          </div>
                          {canManageServices && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full mt-3"
                              onClick={() =>
                                setTemplateDialog({ open: true, service })
                              }
                            >
                              <Users className="h-3 w-3 mr-2" />
                              Staff Roles
                            </Button>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Dialogs */}
      <ServiceDialog
        open={serviceDialog.open}
        service={serviceDialog.service}
        categories={catalog.categories}
        onClose={() => setServiceDialog({ open: false, service: null })}
        onSuccess={() => {
          fetchCatalog();
          setServiceDialog({ open: false, service: null });
        }}
      />

      <CategoryDialog
        open={categoryDialog.open}
        category={categoryDialog.category}
        onClose={() => setCategoryDialog({ open: false, category: null })}
        onSuccess={() => {
          fetchCatalog();
          setCategoryDialog({ open: false, category: null });
        }}
      />

      <ConfirmDialog
        open={deleteDialog.open}
        title={`Delete ${deleteDialog.type === 'service' ? 'Service' : 'Category'}?`}
        description={
          deleteDialog.type === 'service'
            ? 'This service will be soft-deleted and can be restored later.'
            : 'This category and all its services will be deleted. This action cannot be undone.'
        }
        onConfirm={
          deleteDialog.type === 'service'
            ? handleDeleteService
            : handleDeleteCategory
        }
        onCancel={() => setDeleteDialog({ open: false, type: null, id: null })}
      />

      <ImportDialog
        open={importDialog}
        onClose={() => setImportDialog(false)}
        onSuccess={() => {
          fetchCatalog();
          setImportDialog(false);
        }}
      />

      <ServiceStaffTemplateManager
        serviceId={templateDialog.service?.id || null}
        serviceName={templateDialog.service?.name || ''}
        open={templateDialog.open}
        onOpenChange={(open) => setTemplateDialog({ open, service: open ? templateDialog.service : null })}
        onSuccess={() => {
          // Optional: refresh catalog or show indicator
          toast.success('Staff roles updated');
        }}
      />
    </div>
  );
}
