'use client';

import { useState, useEffect, useRef } from 'react';
import { ServiceGrid } from '@/components/pos/service-grid';
import { ProductGrid } from '@/components/pos/product-grid';
import { CartSidebar } from '@/components/pos/cart-sidebar';
import { PaymentModal } from '@/components/pos/payment-modal';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ShoppingCart } from 'lucide-react';
import { useCartStore } from '@/stores/cart-store';
import { useIsMobile } from '@/hooks/use-mobile';

export default function POSPage() {
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const { items } = useCartStore();
  const isMobile = useIsMobile();

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
    <div className="relative">
      <div className="flex gap-4">
        {/* Main Area - Service/Product Selection */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="mb-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h1 className="text-2xl font-bold text-gray-900">Point of Sale</h1>
                <p className="text-sm text-gray-500 mt-1">
                  Select services or products and process payments
                </p>
              </div>
              {/* Mobile Cart Button - Only visible on mobile */}
              {isMobile && (
                <Sheet open={isCartOpen} onOpenChange={setIsCartOpen}>
                  <SheetTrigger asChild>
                    <Button size="lg" className="relative md:hidden">
                      <ShoppingCart className="h-5 w-5" />
                      {items.length > 0 && (
                        <Badge
                          variant="destructive"
                          className="absolute -top-2 -right-2 h-6 w-6 rounded-full p-0 flex items-center justify-center"
                        >
                          {items.length}
                        </Badge>
                      )}
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="right" className="w-full sm:w-96 p-0">
                    <CartSidebar onCheckout={handleCheckout} customerSearchRef={customerSearchRef} />
                  </SheetContent>
                </Sheet>
              )}
            </div>
            <div className="mt-2 text-xs text-gray-400 space-x-4 hidden md:block">
              <span><kbd className="px-1.5 py-0.5 bg-gray-100 rounded border">/</kbd> Search service</span>
              <span><kbd className="px-1.5 py-0.5 bg-gray-100 rounded border">⌘+.</kbd> Select customer</span>
              <span><kbd className="px-1.5 py-0.5 bg-gray-100 rounded border">⌘+↵</kbd> Checkout</span>
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

      {/* Floating Cart Button for Mobile - Bottom Right */}
      {isMobile && !isCartOpen && items.length > 0 && (
        <div className="fixed bottom-6 right-6 z-40 md:hidden">
          <Button
            size="lg"
            onClick={() => setIsCartOpen(true)}
            className="h-16 w-16 rounded-full shadow-lg relative"
          >
            <ShoppingCart className="h-6 w-6" />
            <Badge
              variant="destructive"
              className="absolute -top-1 -right-1 h-7 w-7 rounded-full p-0 flex items-center justify-center text-sm font-bold"
            >
              {items.length}
            </Badge>
          </Button>
        </div>
      )}

      {/* Payment Modal */}
      <PaymentModal
        isOpen={isPaymentModalOpen}
        onClose={() => setIsPaymentModalOpen(false)}
      />
    </div>
  );
}
