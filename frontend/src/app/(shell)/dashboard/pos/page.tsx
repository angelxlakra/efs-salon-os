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

export default function POSPage() {
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const { items } = useCartStore();
  const serviceSearchRef = useRef<HTMLInputElement>(null);
  const customerSearchRef = useRef<{ openSearch: () => void }>(null);

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
        {/* Main Area - Service/Product Selection */}
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

          {/* Tabs for Services and Products */}
          <Tabs defaultValue="services" className="flex-1">
            <TabsList className="mb-4">
              <TabsTrigger value="services">Services</TabsTrigger>
              <TabsTrigger value="products">Products</TabsTrigger>
            </TabsList>

            <TabsContent value="services" className="mt-0">
              <ServiceGrid searchInputRef={serviceSearchRef} />
            </TabsContent>

            <TabsContent value="products" className="mt-0">
              <ProductGrid />
            </TabsContent>
          </Tabs>
        </div>

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
