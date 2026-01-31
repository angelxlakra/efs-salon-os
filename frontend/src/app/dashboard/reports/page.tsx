'use client';

import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, FileText, BarChart3, PieChart } from 'lucide-react';

export default function ReportsPage() {
  const reports = [
    {
      title: 'Profit & Loss Statement',
      description: 'View detailed revenue, costs, and profitability metrics',
      icon: TrendingUp,
      href: '/dashboard/reports/profit-loss',
      iconColor: 'text-green-600',
      bgColor: 'bg-green-50',
    },
    {
      title: 'Daily Summary',
      description: 'Daily revenue, expenses, and transaction summaries',
      icon: FileText,
      href: '/dashboard',
      iconColor: 'text-blue-600',
      bgColor: 'bg-blue-50',
      disabled: true,
    },
    {
      title: 'Sales Analytics',
      description: 'Service and product sales performance over time',
      icon: BarChart3,
      href: '/dashboard',
      iconColor: 'text-purple-600',
      bgColor: 'bg-purple-50',
      disabled: true,
    },
    {
      title: 'Expense Breakdown',
      description: 'Operating expense analysis by category',
      icon: PieChart,
      href: '/dashboard',
      iconColor: 'text-orange-600',
      bgColor: 'bg-orange-50',
      disabled: true,
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Reports</h1>
        <p className="text-muted-foreground">
          Access financial and operational reports for your salon
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {reports.map((report) => {
          const Icon = report.icon;
          const content = (
            <Card className={`hover:shadow-md transition-shadow ${report.disabled ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer hover:border-primary'}`}>
              <CardHeader>
                <div className={`w-12 h-12 rounded-lg ${report.bgColor} flex items-center justify-center mb-3`}>
                  <Icon className={`h-6 w-6 ${report.iconColor}`} />
                </div>
                <CardTitle className="flex items-center justify-between">
                  {report.title}
                  {report.disabled && (
                    <span className="text-xs font-normal text-muted-foreground">Coming Soon</span>
                  )}
                </CardTitle>
                <CardDescription>{report.description}</CardDescription>
              </CardHeader>
            </Card>
          );

          if (report.disabled) {
            return <div key={report.title}>{content}</div>;
          }

          return (
            <Link key={report.title} href={report.href}>
              {content}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
