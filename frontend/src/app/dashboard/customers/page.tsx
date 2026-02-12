'use client';

import { useState, useEffect } from 'react';
import { Plus, Loader2, Edit2, Trash2, Search, User, Wallet, History } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/stores/auth-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { CustomerDialog } from '@/components/customers/customer-dialog';
import { ConfirmDialog } from '@/components/ui/confirm-dialog';
import { CollectPendingPaymentDialog } from '@/components/customers/collect-pending-payment-dialog';
import { PendingPaymentHistory } from '@/components/customers/pending-payment-history';

interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  date_of_birth: string | null;
  gender: string | null;
  notes: string;
  total_visits: number;
  total_spent: number; // in paise
  pending_balance: number; // in paise
  last_visit_at: string | null;
  created_at: string;
}

export default function CustomersPage() {
  const { user } = useAuthStore();
  const isOwner = user?.role === 'owner';
  const canEdit = isOwner || user?.role === 'receptionist';

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCustomers, setTotalCustomers] = useState(0);
  const pageSize = 20;

  // Dialog states
  const [customerDialog, setCustomerDialog] = useState<{ open: boolean; customer: Customer | null }>(
    { open: false, customer: null }
  );
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; id: string | null }>(
    { open: false, id: null }
  );
  const [collectPaymentDialog, setCollectPaymentDialog] = useState<{
    open: boolean;
    customer: Customer | null;
  }>({ open: false, customer: null });
  const [paymentHistoryDialog, setPaymentHistoryDialog] = useState<{
    open: boolean;
    customer: Customer | null;
  }>({ open: false, customer: null });

  useEffect(() => {
    fetchCustomers();
  }, [currentPage, searchQuery]);

  const fetchCustomers = async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams({
        page: currentPage.toString(),
        size: pageSize.toString(),
      });

      if (searchQuery) {
        params.append('search', searchQuery);
      }

      const { data } = await apiClient.get(`/customers?${params}`);
      setCustomers(data.items || []);
      setTotalPages(data.pages || 1);
      setTotalCustomers(data.total || 0);
    } catch (error: any) {
      toast.error('Failed to load customers');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteDialog.id) return;

    try {
      await apiClient.delete(`/customers/${deleteDialog.id}`);
      toast.success('Customer deleted successfully');
      fetchCustomers();
      setDeleteDialog({ open: false, id: null });
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete customer');
    }
  };

  const formatPrice = (paise: number) => {
    return `₹${(paise / 100).toFixed(2)}`;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatPhone = (phone: string | null) => {
    // Format: +91 XXXXX XXXXX
    if (!phone) return '-';
    if (phone.length === 10) {
      return `+91 ${phone.slice(0, 5)} ${phone.slice(5)}`;
    }
    return phone;
  };

  // Reset to page 1 when search changes
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading customers...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Customers</h1>
          <p className="text-sm text-gray-500 mt-1">
            Manage customer database and track visit history
          </p>
        </div>
        {canEdit && (
          <Button onClick={() => setCustomerDialog({ open: true, customer: null })}>
            <Plus className="h-4 w-4 mr-2" />
            Add Customer
          </Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Customers</CardDescription>
            <CardTitle className="text-3xl">{totalCustomers}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Active This Month</CardDescription>
            <CardTitle className="text-3xl">
              {customers.filter((c) => {
                if (!c.last_visit_at) return false;
                const lastVisit = new Date(c.last_visit_at);
                const now = new Date();
                const monthAgo = new Date(now.getFullYear(), now.getMonth(), 1);
                return lastVisit >= monthAgo;
              }).length}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Visits</CardDescription>
            <CardTitle className="text-3xl">
              {customers.reduce((sum, c) => sum + c.total_visits, 0)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Revenue</CardDescription>
            <CardTitle className="text-3xl">
              {formatPrice(customers.reduce((sum, c) => sum + c.total_spent, 0))}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Pending Balance</CardDescription>
            <CardTitle className="text-3xl text-red-600">
              {formatPrice(customers.reduce((sum, c) => sum + (c.pending_balance || 0), 0))}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search by name, phone, or email..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Customer List */}
      {customers.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <User className="h-12 w-12 text-gray-300 mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              {searchQuery ? 'No customers found' : 'No customers yet'}
            </h3>
            <p className="text-gray-500 text-center mb-4">
              {searchQuery
                ? 'Try adjusting your search'
                : 'Add your first customer to get started'}
            </p>
            {canEdit && !searchQuery && (
              <Button onClick={() => setCustomerDialog({ open: true, customer: null })}>
                <Plus className="h-4 w-4 mr-2" />
                Add Customer
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Customer
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Contact
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Visits
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total Spent
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Pending
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Visit
                    </th>
                    {canEdit && (
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {customers.map((customer) => (
                    <tr key={customer.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm font-medium text-gray-900">
                            {customer.first_name} {customer.last_name}
                          </div>
                          {customer.gender && (
                            <div className="text-sm text-gray-500 capitalize">
                              {customer.gender}
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div>
                          <div className="text-sm text-gray-900">
                            {formatPhone(customer.phone)}
                          </div>
                          {customer.email && (
                            <div className="text-sm text-gray-500">{customer.email}</div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Badge variant="secondary">{customer.total_visits}</Badge>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(customer.total_spent)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {customer.pending_balance > 0 ? (
                            <span className="text-red-600 font-medium text-sm">
                              {formatPrice(customer.pending_balance)}
                            </span>
                          ) : (
                            <span className="text-gray-400 text-sm">-</span>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setPaymentHistoryDialog({ open: true, customer })}
                            className="h-6 w-6 p-0"
                            title="View payment history"
                          >
                            <History className="h-3 w-3 text-gray-400" />
                          </Button>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(customer.last_visit_at)}
                      </td>
                      {canEdit && (
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <div className="flex justify-end gap-2">
                            {customer.pending_balance > 0 && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() =>
                                  setCollectPaymentDialog({ open: true, customer })
                                }
                                className="text-green-600 border-green-600 hover:bg-green-50"
                              >
                                <Wallet className="h-4 w-4 mr-1" />
                                Collect
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() =>
                                setCustomerDialog({ open: true, customer })
                              }
                            >
                              <Edit2 className="h-4 w-4" />
                            </Button>
                            {isOwner && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  setDeleteDialog({ open: true, id: customer.id })
                                }
                              >
                                <Trash2 className="h-4 w-4 text-red-600" />
                              </Button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="px-6 py-4 border-t flex items-center justify-between">
                <div className="text-sm text-gray-500">
                  Showing {((currentPage - 1) * pageSize) + 1} to {Math.min(currentPage * pageSize, totalCustomers)} of {totalCustomers} customers
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <div className="flex items-center gap-2 px-3">
                    <span className="text-sm text-gray-700">
                      Page {currentPage} of {totalPages}
                    </span>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Dialogs */}
      <CustomerDialog
        open={customerDialog.open}
        customer={customerDialog.customer}
        onClose={() => setCustomerDialog({ open: false, customer: null })}
        onSuccess={() => {
          fetchCustomers();
          setCustomerDialog({ open: false, customer: null });
        }}
      />

      {collectPaymentDialog.customer && (
        <CollectPendingPaymentDialog
          open={collectPaymentDialog.open}
          onClose={() => setCollectPaymentDialog({ open: false, customer: null })}
          customerId={collectPaymentDialog.customer.id}
          customerName={`${collectPaymentDialog.customer.first_name} ${collectPaymentDialog.customer.last_name || ''}`}
          pendingBalance={collectPaymentDialog.customer.pending_balance}
          onSuccess={() => {
            fetchCustomers();
            setCollectPaymentDialog({ open: false, customer: null });
          }}
        />
      )}

      {paymentHistoryDialog.customer && (
        <PendingPaymentHistory
          open={paymentHistoryDialog.open}
          onClose={() => setPaymentHistoryDialog({ open: false, customer: null })}
          customerId={paymentHistoryDialog.customer.id}
          customerName={`${paymentHistoryDialog.customer.first_name} ${paymentHistoryDialog.customer.last_name || ''}`}
        />
      )}

      <ConfirmDialog
        open={deleteDialog.open}
        title="Delete Customer?"
        description="This customer will be permanently deleted along with their visit history. This action cannot be undone."
        onConfirm={handleDelete}
        onCancel={() => setDeleteDialog({ open: false, id: null })}
      />
    </div>
  );
}
