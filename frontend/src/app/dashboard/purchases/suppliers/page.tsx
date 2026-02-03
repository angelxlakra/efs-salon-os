'use client';

import { useState, useEffect } from 'react';
import { Plus, Search, Edit, Building2, Receipt, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { purchaseApi, Supplier, SupplierListItem, SupplierCreate, SupplierUpdate } from '@/lib/api/purchases';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';

export default function SuppliersPage() {
  const router = useRouter();
  const [suppliers, setSuppliers] = useState<SupplierListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [view, setView] = useState<'list' | 'form'>('list');
  const [editingSupplier, setEditingSupplier] = useState<SupplierListItem | null>(null);

  // Form state
  const [name, setName] = useState('');
  const [contactPerson, setContactPerson] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [address, setAddress] = useState('');
  const [gstin, setGstin] = useState('');
  const [paymentTerms, setPaymentTerms] = useState('');
  const [notes, setNotes] = useState('');
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    loadSuppliers();
  }, []);

  const loadSuppliers = async () => {
    try {
      setLoading(true);
      const response = await purchaseApi.listSuppliers({ size: 100 });
      setSuppliers(response.items || []);
    } catch (error) {
      console.error('Error loading suppliers:', error);
      toast.error('Failed to load suppliers');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenForm = async (supplier?: SupplierListItem) => {
    if (supplier) {
      // Load full supplier details when editing
      try {
        const fullSupplier = await purchaseApi.getSupplier(supplier.id);
        setEditingSupplier(supplier);
        setName(fullSupplier.name);
        setContactPerson(fullSupplier.contact_person || '');
        setPhone(fullSupplier.phone || '');
        setEmail(fullSupplier.email || '');
        setAddress(fullSupplier.address || '');
        setGstin(fullSupplier.gstin || '');
        setPaymentTerms(fullSupplier.payment_terms || '');
        setNotes(fullSupplier.notes || '');
        setIsActive(fullSupplier.is_active);
      } catch (error) {
        console.error('Error loading supplier:', error);
        toast.error('Failed to load supplier details');
        return;
      }
    } else {
      setEditingSupplier(null);
      setName('');
      setContactPerson('');
      setPhone('');
      setEmail('');
      setAddress('');
      setGstin('');
      setPaymentTerms('');
      setNotes('');
      setIsActive(true);
    }
    setView('form');
  };

  const handleCloseForm = () => {
    setView('list');
    setEditingSupplier(null);
  };

  const handleSave = async () => {
    if (!name.trim()) {
      toast.error('Supplier name is required');
      return;
    }

    try {
      if (editingSupplier) {
        const updateData: SupplierUpdate = {
          name: name.trim(),
          contact_person: contactPerson.trim() || undefined,
          phone: phone.trim() || undefined,
          email: email.trim() || undefined,
          address: address.trim() || undefined,
          gstin: gstin.trim() || undefined,
          payment_terms: paymentTerms.trim() || undefined,
          notes: notes.trim() || undefined,
          is_active: isActive,
        };
        await purchaseApi.updateSupplier(editingSupplier.id, updateData);
        toast.success('Supplier updated successfully');
      } else {
        const createData: SupplierCreate = {
          name: name.trim(),
          contact_person: contactPerson.trim() || undefined,
          phone: phone.trim() || undefined,
          email: email.trim() || undefined,
          address: address.trim() || undefined,
          gstin: gstin.trim() || undefined,
          payment_terms: paymentTerms.trim() || undefined,
          notes: notes.trim() || undefined,
        };
        await purchaseApi.createSupplier(createData);
        toast.success('Supplier created successfully');
      }

      handleCloseForm();
      loadSuppliers();
    } catch (error) {
      console.error('Error saving supplier:', error);
      toast.error('Failed to save supplier');
    }
  };

  const formatCurrency = (amount: number) => {
    return `₹${(amount / 100).toFixed(2)}`;
  };

  const filteredSuppliers = suppliers.filter((supplier) =>
    supplier.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    supplier.contact_person?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    supplier.phone?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (view === 'form') {
    return (
      <div className="p-4 md:p-6 space-y-4 md:space-y-6">
        <div className="flex items-center gap-3 md:gap-4">
          <Button variant="ghost" size="icon" onClick={handleCloseForm}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl md:text-3xl font-bold truncate">{editingSupplier ? 'Edit Supplier' : 'Add New Supplier'}</h1>
            <p className="text-sm md:text-base text-muted-foreground truncate">
              {editingSupplier ? `Updating ${editingSupplier.name}` : 'Create a new supplier profile'}
            </p>
          </div>
        </div>

        <div className="max-w-3xl">
          <Card>
            <CardHeader>
              <CardTitle>Supplier Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Supplier Name *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter supplier name"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="contactPerson" className="text-sm">Contact Person</Label>
                  <Input
                    id="contactPerson"
                    value={contactPerson}
                    onChange={(e) => setContactPerson(e.target.value)}
                    placeholder="Name"
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="phone" className="text-sm">Phone</Label>
                  <Input
                    id="phone"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="Contact number"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="supplier@example.com"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="address">Address</Label>
                <Textarea
                  id="address"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Full address"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="gstin" className="text-sm">GSTIN</Label>
                  <Input
                    id="gstin"
                    value={gstin}
                    onChange={(e) => setGstin(e.target.value)}
                    placeholder="GST number"
                    maxLength={15}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="paymentTerms" className="text-sm">Payment Terms</Label>
                  <Input
                    id="paymentTerms"
                    value={paymentTerms}
                    onChange={(e) => setPaymentTerms(e.target.value)}
                    placeholder="e.g., Net 30, 50% advance"
                  />
                </div>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Additional notes about the supplier"
                  rows={3}
                />
              </div>

              {editingSupplier && (
                <div className="flex items-center space-x-2 pt-2">
                  <Switch
                    id="isActive"
                    checked={isActive}
                    onCheckedChange={setIsActive}
                  />
                  <Label htmlFor="isActive">Active Supplier</Label>
                </div>
              )}
            </CardContent>
            <CardFooter className="flex flex-col-reverse sm:flex-row justify-end gap-2 sm:gap-3 border-t pt-4 sm:pt-6">
              <Button variant="outline" onClick={handleCloseForm} className="w-full sm:w-auto">
                Cancel
              </Button>
              <Button onClick={handleSave} className="w-full sm:w-auto">
                {editingSupplier ? 'Update' : 'Create'} Supplier
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 space-y-4 md:space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl md:text-3xl font-bold">Suppliers</h1>
          <p className="text-sm md:text-base text-muted-foreground">Manage your suppliers and vendors</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
          <Button variant="outline" onClick={() => router.push('/dashboard/purchases/invoices')} className="w-full sm:w-auto">
            <Receipt className="mr-2 h-4 w-4" />
            <span className="sm:inline">Invoices</span>
          </Button>
          <Button onClick={() => handleOpenForm()} className="w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" />
            <span className="sm:inline">Add Supplier</span>
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search suppliers by name, contact person, or phone..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Suppliers Grid */}
      {loading ? (
        <div className="text-center py-12">Loading suppliers...</div>
      ) : filteredSuppliers.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Building2 className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              {searchQuery ? 'No suppliers found matching your search' : 'No suppliers yet'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredSuppliers.map((supplier) => (
            <Card key={supplier.id} className="hover:shadow-lg transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{supplier.name}</CardTitle>
                    {supplier.contact_person && (
                      <p className="text-sm text-muted-foreground">{supplier.contact_person}</p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleOpenForm(supplier)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {supplier.phone && (
                  <div className="text-sm">
                    <span className="text-muted-foreground">Phone:</span> {supplier.phone}
                  </div>
                )}

                <div className="pt-2 border-t space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Total Purchases:</span>
                    <span className="font-medium">{formatCurrency(supplier.total_purchases)}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Outstanding:</span>
                    <span className={supplier.total_outstanding > 0 ? 'font-medium text-orange-600' : 'font-medium text-green-600'}>
                      {formatCurrency(supplier.total_outstanding)}
                    </span>
                  </div>
                </div>

                {!supplier.is_active && (
                  <div className="pt-2">
                    <span className="inline-block px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded">
                      Inactive
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
