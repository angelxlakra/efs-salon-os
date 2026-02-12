import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { ExpenseCategory, ExpenseStatus, type ExpenseFilters } from '@/types/expense';
import { useAuthStore } from '@/stores/auth-store';

interface ExpenseFiltersBarProps {
  filters: ExpenseFilters;
  onFiltersChange: (filters: ExpenseFilters) => void;
}

export function ExpenseFiltersBar({ filters, onFiltersChange }: ExpenseFiltersBarProps) {
  const { user } = useAuthStore();

  const updateFilter = (key: keyof ExpenseFilters, value: any) => {
    onFiltersChange({ ...filters, [key]: value, page: 1 });
  };

  // Filter categories based on user role
  const availableCategories = Object.values(ExpenseCategory).filter((cat) => {
    // Receptionist cannot view rent or salary expenses
    if (user?.role === 'receptionist') {
      return cat !== ExpenseCategory.RENT && cat !== ExpenseCategory.SALARIES;
    }
    return true;
  });

  return (
    <div className="flex gap-4 items-end flex-wrap">
      <div className="flex-1 min-w-[200px]">
        <label className="text-sm font-medium text-gray-700 block mb-2">Start Date</label>
        <Input
          type="date"
          value={filters.start_date || ''}
          onChange={(e) => updateFilter('start_date', e.target.value || undefined)}
        />
      </div>

      <div className="flex-1 min-w-[200px]">
        <label className="text-sm font-medium text-gray-700 block mb-2">End Date</label>
        <Input
          type="date"
          value={filters.end_date || ''}
          onChange={(e) => updateFilter('end_date', e.target.value || undefined)}
        />
      </div>

      <div className="flex-1 min-w-[200px]">
        <label className="text-sm font-medium text-gray-700 block mb-2">Category</label>
        <Select
          value={filters.category || 'all'}
          onValueChange={(value) => updateFilter('category', value === 'all' ? undefined : value)}
        >
          <SelectTrigger>
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All categories</SelectItem>
            {availableCategories.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex-1 min-w-[200px]">
        <label className="text-sm font-medium text-gray-700 block mb-2">Status</label>
        <Select
          value={filters.status || 'all'}
          onValueChange={(value) => updateFilter('status', value === 'all' ? undefined : value)}
        >
          <SelectTrigger>
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {Object.values(ExpenseStatus).map((status) => (
              <SelectItem key={status} value={status}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
