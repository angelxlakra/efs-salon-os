'use client';

import { useState, useEffect } from 'react';
import { Plus, Loader2, Edit2, Trash2, FolderPlus, Upload, Users, History, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/auth-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { ServiceDialog } from '@/components/services/service-dialog';
import { CategoryDialog } from '@/components/services/category-dialog';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { ImportDialog } from '@/components/services/import-dialog';
import { ServiceStaffTemplateManager } from '@/components/services/ServiceStaffTemplateManager';
import { ServiceHistoryDialog } from '@/components/services/service-history-dialog';

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
  const [searchQuery, setSearchQuery] = useState('');

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
  const [historyDialog, setHistoryDialog] = useState<{ open: boolean; service: Service | null }>({
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
    let services = catalog.services.filter((s) => s.category_id === categoryId);
    if (searchQuery.trim()) {
      const tokens = searchQuery.toLowerCase().trim().split(/\s+/).filter((t) => t.length > 0);
      services = services.filter((s) =>
        tokens.every((token) => s.name.toLowerCase().includes(token))
      );
    }
    return services;
  };

  const filteredCategories = (() => {
    let cats = selectedCategory
      ? catalog.categories.filter((c) => c.id === selectedCategory)
      : catalog.categories;
    // When searching, hide categories that have no matching services
    if (searchQuery.trim()) {
      cats = cats.filter((c) => getServicesByCategory(c.id).length > 0);
    }
    return cats;
  })();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-text-disabled mx-auto mb-2" />
          <p className="text-sm text-text-muted">Loading services...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Services Management</h1>
          <p className="text-sm text-text-muted mt-1">
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
        <Card density="sm">
          <Card.Header className="pb-3">
            <p className="text-xs text-text-muted">Total Categories</p>
            <p className="text-2xl font-bold text-text-primary">{catalog.categories.length}</p>
          </Card.Header>
        </Card>
        <Card density="sm">
          <Card.Header className="pb-3">
            <p className="text-xs text-text-muted">Total Services</p>
            <p className="text-2xl font-bold text-text-primary">{catalog.services.length}</p>
          </Card.Header>
        </Card>
        <Card density="sm">
          <Card.Header className="pb-3">
            <p className="text-xs text-text-muted">Active Services</p>
            <p className="text-2xl font-bold text-text-primary">
              {catalog.services.filter((s) => s.is_active).length}
            </p>
          </Card.Header>
        </Card>
      </div>

      {/* Search */}
      {catalog.categories.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-disabled" />
          <Input
            type="text"
            placeholder="Search services..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      )}

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
            <FolderPlus className="h-12 w-12 text-text-disabled mb-4" />
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              No categories yet
            </h3>
            <p className="text-text-muted text-center mb-4">
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
      ) : filteredCategories.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <p className="text-text-muted">No services found</p>
          {searchQuery && (
            <Button variant="link" onClick={() => setSearchQuery('')} className="mt-2">
              Clear search
            </Button>
          )}
        </div>
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
                    <div className="text-center py-8 text-text-muted">
                      No services in this category yet
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {services.map((service) => (
                        <div
                          key={service.id}
                          className="border rounded-lg p-4 hover:border-border-strong transition-colors"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <h4 className="font-semibold text-text-primary">
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
                            <p className="text-sm text-text-muted mb-3">
                              {service.description}
                            </p>
                          )}
                          <div className="flex items-center justify-between text-sm">
                            <span className="font-semibold text-lg text-text-primary">
                              {formatPrice(service.base_price)}
                            </span>
                            <span className="text-text-muted">
                              {service.duration_minutes} min
                            </span>
                          </div>
                          {canManageServices && (
                            <div className="flex gap-2 mt-3">
                              <Button
                                variant="outline"
                                size="sm"
                                className="flex-1"
                                onClick={() =>
                                  setTemplateDialog({ open: true, service })
                                }
                              >
                                <Users className="h-3 w-3 mr-2" />
                                Staff Roles
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="flex-1"
                                onClick={() =>
                                  setHistoryDialog({ open: true, service })
                                }
                                title="View service history"
                              >
                                <History className="h-3 w-3 mr-2" />
                                History
                              </Button>
                            </div>
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

      {historyDialog.service && (
        <ServiceHistoryDialog
          open={historyDialog.open}
          onClose={() => setHistoryDialog({ open: false, service: null })}
          serviceId={historyDialog.service.id}
          serviceName={historyDialog.service.name}
        />
      )}
    </div>
  );
}
