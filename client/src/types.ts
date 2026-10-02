export interface DashboardData {
  metadata: {
    seed: number;
    sourceProfile: string;
    calendarProfile: string;
    startDate: string;
    endDate: string;
    days: number;
  };
  summary: {
    customers: number;
    accounts: number;
    transactions: number;
    events: number;
    loans: number;
    approvedApplications: number;
    anomalies: number;
    anomalyRatePct: number;
    amountTotalVnd: number;
  };
  monthlyTraffic: Array<{
    month: string;
    transactions: number;
    dailyAverage: number;
    amountTotalVnd: number;
    dailyChangePct: number | null;
    anomalies: number;
  }>;
  specialDayTraffic: Array<{
    tag: string;
    days: number;
    transactionsPerDay: number;
    transactionChangePct: number | null;
    amountPerDayVnd: number;
    amountChangePct: number | null;
  }>;
  fieldRanges: Array<{
    field: string;
    kind: "range";
    min: number;
    max: number;
    unit: string;
  }>;
  fieldHistograms: Array<{
    field: string;
    min: number;
    max: number;
    bins: Array<{
      min: number;
      max: number;
      count: number;
      months: Record<string, number>;
    }>;
  }>;
  categories: Array<{
    name: string;
    values: Array<{ label: string; count: number }>;
  }>;
}
