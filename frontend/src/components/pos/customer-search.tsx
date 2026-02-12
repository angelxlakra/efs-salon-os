'use client';

import { useState, useEffect } from 'react';
import { Check, ChevronsUpDown, Plus, User, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { apiClient } from '@/lib/api-client';
import { cn } from '@/lib/utils';
import { CustomerDialog } from '@/components/customers/customer-dialog';

interface Customer {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string;
  total_visits: number;
  total_spent: number;
  pending_balance: number;
  pending_balance_rupees: number;
}

interface CustomerSearchProps {
  value: { id: string | null; name: string | null };
  onChange: (customerId: string | null, customerName: string | null, customerPhone?: string | null) => void;
  isOpen?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function CustomerSearch({ value, onChange, isOpen, onOpenChange }: CustomerSearchProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = isOpen !== undefined ? isOpen : internalOpen;
  const setOpen = onOpenChange || setInternalOpen;
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [search, setSearch] = useState('');
  const [showDialog, setShowDialog] = useState(false);

  // Debounced search - fetch from server when user types
  useEffect(() => {
    if (search.length >= 2) {
      const timer = setTimeout(() => {
        fetchCustomers(search);
      }, 300); // 300ms debounce
      return () => clearTimeout(timer);
    } else if (search.length === 0) {
      setCustomers([]);
    }
  }, [search]);

  const fetchCustomers = async (query: string) => {
    try {
      // Use new autocomplete endpoint - searches ALL customers
      const { data } = await apiClient.get(`/customers/autocomplete?q=${encodeURIComponent(query)}&limit=10`);
      setCustomers(data.items || []);
    } catch (error) {
      console.error('Failed to fetch customers:', error);
    }
  };

  const formatPhone = (phone: string | null) => {
    if (!phone) return '-';
    if (phone.length === 10) {
      return `+91 ${phone.slice(0, 5)} ${phone.slice(5)}`;
    }
    return phone;
  };

  const handleSelect = (customer: Customer) => {
    console.log('Customer selected:', customer);
    const fullName = `${customer.first_name} ${customer.last_name}`;
    console.log('Calling onChange with:', customer.id, fullName, customer.phone);
    onChange(customer.id, fullName, customer.phone);
    console.log('Setting popover open to false');
    setOpen(false);
  };

  const handleClear = () => {
    onChange(null, null, null);
  };

  const handleWalkIn = () => {
    onChange(null, 'Walk-in Customer', null);
    setOpen(false);
  };

  const handleOpenChange = (newOpen: boolean) => {
    console.log('Customer search popover state changing to:', newOpen);
    setOpen(newOpen);
  };

  return (
    <>
      <div className="flex gap-2 relative">
        <Popover open={open} onOpenChange={handleOpenChange}>
          <PopoverTrigger asChild>
            <button
              role="combobox"
              aria-expanded={open}
              className="flex-1 flex items-center justify-between h-9 px-3 py-2 text-sm rounded-md border border-input bg-background hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring cursor-pointer pointer-events-auto"
              style={{ pointerEvents: 'auto' }}
              type="button"
              onClick={(e) => {
                console.log('Customer button clicked!', e);
              }}
              onPointerDown={(e) => {
                console.log('Customer button pointer down!', e);
              }}
              onMouseDown={(e) => {
                console.log('Customer button mouse down!', e);
              }}
            >
              <div className="flex items-center gap-2 truncate flex-1 min-w-0">
                <User className="h-4 w-4 shrink-0" />
                <span className="truncate">
                  {value.name || 'Select customer'}
                </span>
              </div>
              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-[300px] p-0" align="start">
            <Command shouldFilter={false}>
              <CommandInput
                placeholder="Search by name or phone..."
                value={search}
                onValueChange={setSearch}
              />
              <CommandList>
                {search.length >= 2 && customers.length > 0 && (
                  <CommandGroup heading="Customers">
                    {customers.map((customer) => (
                      <CommandItem
                        key={customer.id}
                        value={customer.id}
                        onSelect={() => {
                          console.log('onSelect triggered for:', customer);
                          handleSelect(customer);
                        }}
                        onPointerDown={(e: React.PointerEvent) => {
                          console.log('onPointerDown triggered for:', customer);
                          e.preventDefault();
                          handleSelect(customer);
                        }}
                        className="cursor-pointer hover:bg-accent"
                      >
                        <Check
                          className={cn(
                            'mr-2 h-4 w-4',
                            value.id === customer.id ? 'opacity-100' : 'opacity-0'
                          )}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate">
                            {customer.first_name} {customer.last_name}
                          </div>
                          <div className="text-xs text-gray-500">
                            {formatPhone(customer.phone)} • {customer.total_visits} visits
                          </div>
                          {customer.pending_balance > 0 && (
                            <div className="text-xs text-red-600 font-medium">
                              Pending: ₹{(customer.pending_balance / 100).toFixed(2)}
                            </div>
                          )}
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                )}
                {search.length >= 2 && customers.length === 0 && (
                  <div className="py-6 text-center text-sm text-gray-500">
                    No customers found
                  </div>
                )}
                {search.length > 0 && search.length < 2 && (
                  <div className="py-6 text-center text-sm text-gray-500">
                    Type at least 2 characters to search
                  </div>
                )}
                <CommandGroup>
                  <CommandItem
                    onSelect={() => {
                      console.log('Add New Customer - onSelect');
                      setOpen(false);
                      setTimeout(() => setShowDialog(true), 100);
                    }}
                    onPointerDown={(e: React.PointerEvent) => {
                      console.log('Add New Customer - onPointerDown');
                      e.preventDefault();
                      setOpen(false);
                      setTimeout(() => setShowDialog(true), 100);
                    }}
                    className="cursor-pointer text-primary hover:bg-accent"
                  >
                    <Plus className="mr-2 h-4 w-4" />
                    <span>Add New Customer</span>
                  </CommandItem>
                  <CommandItem
                    onSelect={() => {
                      console.log('Walk-in - onSelect');
                      handleWalkIn();
                    }}
                    onPointerDown={(e: React.PointerEvent) => {
                      console.log('Walk-in - onPointerDown');
                      e.preventDefault();
                      handleWalkIn();
                    }}
                    className="cursor-pointer hover:bg-accent"
                  >
                    <User className="mr-2 h-4 w-4" />
                    <span>Walk-in Customer</span>
                  </CommandItem>
                </CommandGroup>
              </CommandList>
            </Command>
          </PopoverContent>
        </Popover>

        {value.name && (
          <Button variant="ghost" size="sm" onClick={handleClear}>
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>

      <CustomerDialog
        open={showDialog}
        customer={null}
        initialPhone={search}
        onClose={() => setShowDialog(false)}
        onSuccess={(created) => {
          setShowDialog(false);
          if (created) {
            const fullName = `${created.first_name} ${created.last_name}`.trim();
            onChange(created.id, fullName, created.phone);
          } else {
            fetchCustomers(search);
          }
        }}
      />
    </>
  );
}
