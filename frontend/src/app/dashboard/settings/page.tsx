'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { useAuthStore } from '@/stores/auth-store';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import {
  Settings,
  Building2,
  MapPin,
  Phone,
  Mail,
  Globe,
  FileText,
  Receipt,
  Palette,
  Save,
  Loader2,
  AlertCircle,
  RotateCcw
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export default function SettingsPage() {
  const { user } = useAuthStore();
  const isOwner = user?.role === 'owner';

  const [settings, setSettings] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [hasMounted, setHasMounted] = useState(false);

  const [formData, setFormData] = useState({
    salon_name: '',
    salon_tagline: '',
    salon_address: '',
    salon_city: '',
    salon_state: '',
    salon_pincode: '',
    contact_phone: '',
    contact_email: '',
    contact_website: '',
    gstin: '',
    pan: '',
    receipt_header_text: '',
    receipt_footer_text: '',
    receipt_show_gstin: true,
    receipt_show_logo: false,
    logo_url: '',
    primary_color: '#000000',
    invoice_prefix: 'SAL',
    invoice_terms: '',
  });

  useEffect(() => {
    setHasMounted(true);
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setIsLoading(true);
      const { data } = await apiClient.get('/settings');
      setSettings(data);
      setFormData({
        salon_name: data.salon_name || '',
        salon_tagline: data.salon_tagline || '',
        salon_address: data.salon_address || '',
        salon_city: data.salon_city || '',
        salon_state: data.salon_state || '',
        salon_pincode: data.salon_pincode || '',
        contact_phone: data.contact_phone || '',
        contact_email: data.contact_email || '',
        contact_website: data.contact_website || '',
        gstin: data.gstin || '',
        pan: data.pan || '',
        receipt_header_text: data.receipt_header_text || '',
        receipt_footer_text: data.receipt_footer_text || '',
        receipt_show_gstin: data.receipt_show_gstin ?? true,
        receipt_show_logo: data.receipt_show_logo ?? false,
        logo_url: data.logo_url || '',
        primary_color: data.primary_color || '#000000',
        invoice_prefix: data.invoice_prefix || 'SAL',
        invoice_terms: data.invoice_terms || '',
      });
      setHasChanges(false);
    } catch (error: any) {
      toast.error('Failed to load settings');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (!isOwner) {
      toast.error('Only owners can update salon settings');
      return;
    }

    try {
      setIsSaving(true);
      await apiClient.patch('/settings', formData);
      toast.success('Settings updated successfully');
      setHasChanges(false);
      fetchSettings();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update settings');
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Are you sure you want to reset all settings to default values? This action cannot be undone.')) {
      return;
    }

    try {
      setIsSaving(true);
      await apiClient.post('/settings/reset');
      toast.success('Settings reset to defaults');
      setHasChanges(false);
      fetchSettings();
    } catch (error: any) {
      toast.error('Failed to reset settings');
      console.error(error);
    } finally {
      setIsSaving(false);
    }
  };

  if (!hasMounted) {
    return null;
  }

  if (!isOwner) {
    return (
      <div className="space-y-8">
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Only owners can access and modify salon settings.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading settings...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-10">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900 flex items-center gap-2">
            <Settings className="h-8 w-8" />
            Salon Settings
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your salon's business information and receipt customization.
          </p>
        </div>
        <div className="flex gap-2">
          {hasChanges && (
            <Button variant="outline" onClick={() => fetchSettings()} disabled={isSaving}>
              Cancel
            </Button>
          )}
          <Button onClick={handleSave} disabled={!hasChanges || isSaving}>
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Business Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Business Information
          </CardTitle>
          <CardDescription>
            Basic information about your salon that appears on receipts and invoices.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="salon_name">Salon Name *</Label>
              <Input
                id="salon_name"
                value={formData.salon_name}
                onChange={(e) => handleChange('salon_name', e.target.value)}
                placeholder="e.g., Glamour Beauty Salon"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="salon_tagline">Tagline</Label>
              <Input
                id="salon_tagline"
                value={formData.salon_tagline}
                onChange={(e) => handleChange('salon_tagline', e.target.value)}
                placeholder="e.g., Where Beauty Meets Excellence"
              />
            </div>
          </div>

          <Separator />

          <div className="space-y-2">
            <Label htmlFor="salon_address">Address *</Label>
            <Textarea
              id="salon_address"
              value={formData.salon_address}
              onChange={(e) => handleChange('salon_address', e.target.value)}
              placeholder="e.g., Shop No. 45, Main Street"
              rows={2}
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="salon_city">City</Label>
              <Input
                id="salon_city"
                value={formData.salon_city}
                onChange={(e) => handleChange('salon_city', e.target.value)}
                placeholder="e.g., Mumbai"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="salon_state">State</Label>
              <Input
                id="salon_state"
                value={formData.salon_state}
                onChange={(e) => handleChange('salon_state', e.target.value)}
                placeholder="e.g., Maharashtra"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="salon_pincode">Pincode</Label>
              <Input
                id="salon_pincode"
                value={formData.salon_pincode}
                onChange={(e) => handleChange('salon_pincode', e.target.value)}
                placeholder="e.g., 400001"
                maxLength={6}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Contact Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Contact Information
          </CardTitle>
          <CardDescription>
            Contact details displayed on receipts and customer communications.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="contact_phone">Phone Number</Label>
              <div className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <Input
                  id="contact_phone"
                  value={formData.contact_phone}
                  onChange={(e) => handleChange('contact_phone', e.target.value)}
                  placeholder="+91 98765 43210"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_email">Email Address</Label>
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <Input
                  id="contact_email"
                  type="email"
                  value={formData.contact_email}
                  onChange={(e) => handleChange('contact_email', e.target.value)}
                  placeholder="salon@example.com"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_website">Website</Label>
              <div className="flex items-center gap-2">
                <Globe className="h-4 w-4 text-muted-foreground" />
                <Input
                  id="contact_website"
                  value={formData.contact_website}
                  onChange={(e) => handleChange('contact_website', e.target.value)}
                  placeholder="www.yoursalon.com"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tax Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Tax Information
          </CardTitle>
          <CardDescription>
            GST and PAN details for tax invoices and compliance.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="gstin">GSTIN (15 characters)</Label>
              <Input
                id="gstin"
                value={formData.gstin}
                onChange={(e) => handleChange('gstin', e.target.value.toUpperCase())}
                placeholder="29XXXXX1234X1ZX"
                maxLength={15}
              />
              <p className="text-xs text-muted-foreground">
                GST Identification Number for tax invoices
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="pan">PAN (10 characters)</Label>
              <Input
                id="pan"
                value={formData.pan}
                onChange={(e) => handleChange('pan', e.target.value.toUpperCase())}
                placeholder="ABCDE1234F"
                maxLength={10}
              />
              <p className="text-xs text-muted-foreground">
                Permanent Account Number
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Receipt Customization */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="h-5 w-5" />
            Receipt Customization
          </CardTitle>
          <CardDescription>
            Customize how your receipts appear (optimized for 80mm thermal printers).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="receipt_header_text">Header Text</Label>
            <Textarea
              id="receipt_header_text"
              value={formData.receipt_header_text}
              onChange={(e) => handleChange('receipt_header_text', e.target.value)}
              placeholder="e.g., Welcome! We're glad to serve you."
              rows={2}
            />
            <p className="text-xs text-muted-foreground">
              Custom message displayed at the top of receipts
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="receipt_footer_text">Footer Text</Label>
            <Textarea
              id="receipt_footer_text"
              value={formData.receipt_footer_text}
              onChange={(e) => handleChange('receipt_footer_text', e.target.value)}
              placeholder="e.g., Thank you for your visit! See you soon."
              rows={2}
            />
            <p className="text-xs text-muted-foreground">
              Custom message displayed at the bottom of receipts
            </p>
          </div>

          <Separator />

          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="receipt_show_gstin">Show GSTIN on Receipts</Label>
                <p className="text-xs text-muted-foreground">
                  Display GST Identification Number on printed receipts
                </p>
              </div>
              <Switch
                id="receipt_show_gstin"
                checked={formData.receipt_show_gstin}
                onCheckedChange={(checked) => handleChange('receipt_show_gstin', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="receipt_show_logo">Show Logo on Receipts</Label>
                <p className="text-xs text-muted-foreground">
                  Display salon logo on printed receipts (if configured)
                </p>
              </div>
              <Switch
                id="receipt_show_logo"
                checked={formData.receipt_show_logo}
                onCheckedChange={(checked) => handleChange('receipt_show_logo', checked)}
                disabled
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Invoice Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Invoice Settings
          </CardTitle>
          <CardDescription>
            Configure invoice numbering and terms & conditions.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="invoice_prefix">Invoice Prefix</Label>
            <Input
              id="invoice_prefix"
              value={formData.invoice_prefix}
              onChange={(e) => handleChange('invoice_prefix', e.target.value.toUpperCase())}
              placeholder="SAL"
              maxLength={10}
            />
            <p className="text-xs text-muted-foreground">
              Invoice format: {formData.invoice_prefix}-YY-NNNN (e.g., {formData.invoice_prefix}-26-0001)
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="invoice_terms">Terms & Conditions</Label>
            <Textarea
              id="invoice_terms"
              value={formData.invoice_terms}
              onChange={(e) => handleChange('invoice_terms', e.target.value)}
              placeholder="e.g., All services are non-refundable. Advance booking required for premium services."
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              Terms displayed on invoices (optional)
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            Danger Zone
          </CardTitle>
          <CardDescription>
            Irreversible actions that affect your salon configuration.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium">Reset to Default Settings</h4>
              <p className="text-sm text-muted-foreground">
                Reset all settings to factory defaults. This action cannot be undone.
              </p>
            </div>
            <Button
              variant="destructive"
              onClick={handleReset}
              disabled={isSaving}
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset All
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
