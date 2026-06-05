'use client';

import { useState, useEffect, useRef } from 'react';
import { ServiceGrid } from '@/components/pos/service-grid';
import { ProductGrid } from '@/components/pos/product-grid';
import { CartSidebar } from '@/components/pos/cart-sidebar';
import { PaymentModal } from '@/components/pos/payment-modal';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sheet, SheetContent } from '@/components/ui/sheet';
import { ShoppingCart } from 'lucide-react';
import { useCartStore } from '@/stores/cart-store';
import { EntitlementsRail } from '@/components/packages/EntitlementsRail';
import { PackageSelectorChip } from '@/components/packages/PackageSelectorChip';
import { usePackagesStore } from '@/stores/packages-store';

// ---------------------------------------------------------------------------
// Inline component: grid of published packages for POS selection
// ---------------------------------------------------------------------------
function PackagesSelectorView() {
  const definitions = usePackagesStore((s) => s.definitions);

  if (!definitions || definitions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-muted-foreground">No published packages</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 p-1">
      {definitions
        .filter((d) => d.status === 'published')
        .map((pkg) => (
          <button
            key={pkg.id}
            type="button"
            className="rounded-xl border border-border bg-card p-4 text-left hover:border-accent transition-colors"
            onClick={() => {
              // TODO: add package_sale_line item to bill (requires backend integration)
            }}
          >
            <p className="font-medium text-sm">{pkg.name}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {pkg.entitlement_type === 'counted'
                ? `${pkg.total_sessions} sessions · ${pkg.validity_days}d`
                : `Unlimited · ${pkg.validity_days}d`}
            </p>
            <p className="text-sm font-semibold tabular-nums mt-2">
              ₹
              {(
                pkg.items.reduce(
                  (s, i) => s + i.unit_price_paise * i.quantity,
                  0
                ) / 100
              ).toFixed(0)}
            </p>
          </button>
        ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main POS page
// ---------------------------------------------------------------------------
export default function POSPage() {
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'services' | 'products' | 'packages'>('services');
  const { items, customerId } = useCartStore();
  const serviceSearchRef = useRef<HTMLInputElement>(null);
  const customerSearchRef = useRef<{ openSearch: () => void }>(null);

  // Load published package definitions for the chip count + grid
  const definitions = usePackagesStore((s) => s.definitions);
  const packageCount = definitions?.length ?? 0;

  useEffect(() => {
    usePackagesStore.getState().loadDefinitions();
  }, []);

  const handleCheckout = () => {
    if (items.length === 0) return;
    setIsCartOpen(false); // Close cart sheet on mobile
    setIsPaymentModalOpen(true);
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Slash key - Focus service search
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        // Check if user is not already typing in an input/textarea
        const activeElement = document.activeElement;
        if (
          activeElement?.tagName !== 'INPUT' &&
          activeElement?.tagName !== 'TEXTAREA'
        ) {
          e.preventDefault();
          serviceSearchRef.current?.focus();
        }
      }

      // Cmd+. or Ctrl+. - Open customer search
      if (e.key === '.' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        customerSearchRef.current?.openSearch();
      }

      // Cmd+Enter or Ctrl+Enter - Open payment modal
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleCheckout();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [items.length]);

  return (
    <div className="relative p-4 md:p-6">
      <div className="flex gap-4">
        {/* Main Area - Service/Product/Package Selection */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="mb-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h1 className="text-xl font-semibold text-text-primary">Point of Sale</h1>
                <p className="text-sm text-text-secondary mt-1">
                  Select services or products and process payments
                </p>
              </div>
            </div>
            <div className="mt-2 text-xs text-text-muted space-x-4 hidden md:block">
              <span><kbd className="px-1.5 py-0.5 bg-surface-row rounded border border-border-subtle">/</kbd> Search service</span>
              <span><kbd className="px-1.5 py-0.5 bg-surface-row rounded border border-border-subtle">⌘+.</kbd> Select customer</span>
              <span><kbd className="px-1.5 py-0.5 bg-surface-row rounded border border-border-subtle">⌘+↵</kbd> Checkout</span>
            </div>
          </div>

          {/* Tabs for Services, Products, and Packages */}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-4">
              <Tabs
                value={activeTab === 'packages' ? 'services' : activeTab}
                onValueChange={(v) => setActiveTab(v as 'services' | 'products')}
                className="flex-1"
              >
                <TabsList>
                  <TabsTrigger value="services">Services</TabsTrigger>
                  <TabsTrigger value="products">Products</TabsTrigger>
                </TabsList>
              </Tabs>
              <PackageSelectorChip
                active={activeTab === 'packages'}
                onClick={() =>
                  setActiveTab(activeTab === 'packages' ? 'services' : 'packages')
                }
                count={packageCount}
              />
            </div>

            {activeTab === 'services' && (
              <ServiceGrid searchInputRef={serviceSearchRef} />
            )}
            {activeTab === 'products' && <ProductGrid />}
            {activeTab === 'packages' && <PackagesSelectorView />}
          </div>
        </div>

        {/* Entitlements Rail — desktop only, only when a customer is selected */}
        {customerId && (
          <div className="hidden lg:block">
            <EntitlementsRail customerId={customerId} />
          </div>
        )}

        {/* Right Sidebar - Cart (Desktop Only) */}
        <div className="w-96 flex-shrink-0 hidden md:block">
          <CartSidebar onCheckout={handleCheckout} customerSearchRef={customerSearchRef} />
        </div>
      </div>

      {/* Mobile cart FAB */}
      {items.length > 0 && (
        <button
          type="button"
          className="fixed bottom-20 right-4 z-40 flex md:hidden items-center justify-center h-14 w-14 rounded-full bg-accent text-white shadow-lg shadow-accent/30 transition-transform active:scale-95"
          onClick={() => setIsCartOpen(true)}
          aria-label="Open cart"
        >
          <ShoppingCart className="h-6 w-6" />
          <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-surface-card text-accent border border-border-subtle text-[10px] font-bold">
            {items.length}
          </span>
        </button>
      )}

      {/* Mobile cart sheet */}
      <Sheet open={isCartOpen} onOpenChange={setIsCartOpen}>
        <SheetContent side="bottom" className="h-[85vh] bg-surface-card border-border-subtle rounded-t-xl p-0">
          <CartSidebar onCheckout={handleCheckout} customerSearchRef={customerSearchRef} />
        </SheetContent>
      </Sheet>

      {/* Payment Modal */}
      <PaymentModal
        isOpen={isPaymentModalOpen}
        onClose={() => setIsPaymentModalOpen(false)}
      />
    </div>
  );
}
