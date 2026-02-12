/**
 * WhatsApp receipt sharing utilities.
 * Uses wa.me links to open WhatsApp with a pre-filled receipt message.
 */

interface BillItem {
  item_name: string;
  quantity: number;
  line_total: number; // paise
}

interface BillData {
  invoice_number: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  items: BillItem[];
  subtotal: number; // paise
  discount_amount: number; // paise
  rounded_total: number; // paise
  payments: { payment_method: string }[];
  posted_at: string | null;
  created_at: string;
}

function formatPaise(paise: number): string {
  return `\u20B9${(paise / 100).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Normalize an Indian phone number for WhatsApp wa.me links.
 * Strips formatting characters, ensures 91 country code prefix.
 */
export function normalizePhone(phone: string): string {
  // Strip spaces, dashes, parentheses, dots
  let cleaned = phone.replace(/[\s\-().]/g, '');

  // Strip leading +
  if (cleaned.startsWith('+')) {
    cleaned = cleaned.slice(1);
  }

  // If starts with 0 (local format like 09876543210), replace with 91
  if (cleaned.startsWith('0')) {
    cleaned = '91' + cleaned.slice(1);
  }

  // If 10 digits (no country code), prepend 91
  if (cleaned.length === 10 && !cleaned.startsWith('91')) {
    cleaned = '91' + cleaned;
  }

  return cleaned;
}

/**
 * Format bill data into a plain-text receipt suitable for WhatsApp.
 */
export function formatReceiptForWhatsApp(bill: BillData, salonName?: string): string {
  const lines: string[] = [];

  lines.push(`*Receipt from ${salonName || 'Our Salon'}*`);
  lines.push('');

  if (bill.invoice_number) {
    lines.push(`Invoice: ${bill.invoice_number}`);
  }

  const dateStr = bill.posted_at || bill.created_at;
  lines.push(`Date: ${formatDate(dateStr)}`);

  if (bill.customer_name) {
    lines.push(`Customer: ${bill.customer_name}`);
  }

  lines.push('');
  lines.push('Services:');
  for (const item of bill.items) {
    lines.push(`\u2022 ${item.item_name} \u00D7 ${item.quantity} \u2014 ${formatPaise(item.line_total)}`);
  }

  lines.push('');
  lines.push(`Subtotal: ${formatPaise(bill.subtotal)}`);

  if (bill.discount_amount > 0) {
    lines.push(`Discount: -${formatPaise(bill.discount_amount)}`);
  }

  lines.push(`Total: ${formatPaise(bill.rounded_total)}`);

  // Payment method summary
  if (bill.payments && bill.payments.length > 0) {
    const methods = [...new Set(bill.payments.map((p) => p.payment_method))];
    const methodLabels = methods.map((m) => {
      switch (m) {
        case 'cash': return 'Cash';
        case 'upi': return 'UPI';
        case 'card': return 'Card';
        default: return m;
      }
    });
    lines.push(`Payment: ${methodLabels.join(', ')}`);
  }

  lines.push('');
  lines.push('Thank you for visiting!');

  return lines.join('\n');
}

/**
 * Build a WhatsApp wa.me link with pre-filled message.
 */
export function getWhatsAppLink(phone: string, message: string): string {
  const normalized = normalizePhone(phone);
  const encoded = encodeURIComponent(message);
  return `https://wa.me/${normalized}?text=${encoded}`;
}

/**
 * Open WhatsApp with a receipt message for the given bill.
 * Returns false if the customer has no phone number.
 */
export function sendReceiptToWhatsApp(bill: BillData, salonName?: string): boolean {
  if (!bill.customer_phone) {
    return false;
  }

  const message = formatReceiptForWhatsApp(bill, salonName);
  const url = getWhatsAppLink(bill.customer_phone, message);
  window.open(url, '_blank');
  return true;
}
