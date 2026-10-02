import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { DashboardData } from "./types";

const number = new Intl.NumberFormat("vi-VN");
const compact = new Intl.NumberFormat("vi-VN", { notation: "compact", maximumFractionDigits: 1 });
const money = (value: number) => `${compact.format(value)} ₫`;
const monthLabel = (value: string) =>
  new Date(`${value}-01T00:00:00`).toLocaleDateString("vi-VN", { month: "short", year: "2-digit" });

const tagNames: Record<string, string> = {
  payday: "Ngày nhận lương",
  month_end: "Cuối tháng",
  tet_period: "Tết Nguyên đán",
  hung_kings: "Giỗ Tổ Hùng Vương",
  reunification_day: "Ngày 30/4",
  labor_day: "Quốc tế Lao động",
  holiday_bridge: "Kỳ nghỉ lễ",
  family_day: "Ngày Gia đình Việt Nam",
  new_year: "Tết Dương lịch",
};

function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [selectedMonth, setSelectedMonth] = useState("");
  const [search, setSearch] = useState("");
  const [fieldGroup, setFieldGroup] = useState("all");
  const [trendField, setTrendField] = useState("Transaction amount");
  const [chartMode, setChartMode] = useState<"transactions" | "amount">("transactions");

  useEffect(() => {
    fetch("/dashboard.json", { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Chưa có dashboard.json");
        return response.json() as Promise<DashboardData>;
      })
      .then((payload) => {
        setData(payload);
        setSelectedMonth(payload.monthlyTraffic.at(-1)?.month ?? "");
      })
      .catch(() => setError("Chưa có dữ liệu hiển thị. Hãy chạy `make pipeline` để sinh dữ liệu và cập nhật báo cáo."));
  }, []);

  const selected = data?.monthlyTraffic.find((row) => row.month === selectedMonth) ?? data?.monthlyTraffic.at(-1);
  const maxMonthly = Math.max(...(data?.monthlyTraffic.map((row) => chartMode === "transactions" ? row.dailyAverage : row.amountTotalVnd) ?? [1]));
  const transactionTypes = data?.categories.find((item) => item.name === "Transaction type")?.values ?? [];
  const typeTotal = transactionTypes.reduce((sum, item) => sum + item.count, 0);
  const donutStyle = useMemo(() => {
    let cursor = 0;
    const palette = ["#385d50", "#d99b63", "#84a89a", "#e6c9a5", "#a7b8a5"];
    const stops = transactionTypes.map((item, index) => {
      const start = cursor;
      cursor += typeTotal ? (item.count / typeTotal) * 100 : 0;
      return `${palette[index % palette.length]} ${start}% ${cursor}%`;
    });
    return { background: `conic-gradient(${stops.join(",")})` };
  }, [transactionTypes, typeTotal]);

  const filteredFields = (data?.fieldRanges ?? []).filter((item) =>
    (fieldGroup === "all" || fieldGroupFor(item.field) === fieldGroup) &&
    `${fieldLabel(item.field)} ${item.field}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
  );
  const trendFields = (data?.fieldRanges ?? []).filter((item) => (data?.fieldHistograms ?? []).some((histogram) => histogram.field === item.field));
  const selectedTrendField = trendFields.some((item) => item.field === trendField) ? trendField : trendFields[0]?.field ?? "";
  const selectedHistogram = data?.fieldHistograms.find((item) => item.field === selectedTrendField);
  const histogramMonths = data?.monthlyTraffic.map((item) => item.month) ?? [];
  const maxHistogramCount = Math.max(...(selectedHistogram?.bins.flatMap((bin) => histogramMonths.map((month) => bin.months[month] ?? 0)) ?? [1]), 1);
  const topCalendar = (data?.specialDayTraffic ?? [])
    .filter((item) => item.tag !== "regular")
    .sort((a, b) => (b.transactionChangePct ?? 0) - (a.transactionChangePct ?? 0))
    .slice(0, 7);

  if (!data) {
    return <div className="loading-screen"><div className="loading-mark">A</div><h1>Anomaly Data Studio</h1><p>{error || "Đang đọc báo cáo dữ liệu…"}</p>{error && <code>make pipeline</code>}</div>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="Anomaly Data Studio">
          <span className="brand-mark">A</span><span><b>ANOMALY</b><small>DATA STUDIO</small></span>
        </a>
        <div className="side-label">BÁO CÁO</div>
        <nav className="side-nav">
          <a className="active" href="#overview"><span className="nav-icon">◫</span>Tổng quan</a>
          <a href="#traffic"><span className="nav-icon">⌁</span>Lưu lượng</a>
          <a href="#fields"><span className="nav-icon">▤</span>Trường dữ liệu</a>
        </nav>
        <div className="sidebar-bottom">
          <div className="side-label">NGUỒN DỮ LIỆU</div>
          <div className="profile-chip"><span className="status-dot"/><span><b>PaySim inspired</b><small>Dữ liệu mô phỏng</small></span></div>
          <div className="sidebar-foot">Anomaly Data Pipeline <span>v0.1</span></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs">Báo cáo <span>/</span> <b>Phân tích dataset</b></div>
          <div className="top-actions">
            <span className="seed-badge"><i/> Seed {data.metadata.seed}</span>
            <a className="export-button" href="/monthly-traffic.csv" download><span>↓</span> Tải CSV</a>
          </div>
        </header>

        <div className="page-wrap" id="overview">
          <section className="page-heading">
            <div>
              <div className="eyebrow">DATASET MÔ PHỎNG · {data.metadata.days} NGÀY</div>
              <h1>Phân tích dữ liệu</h1>
              <p className="subtitle">Theo dõi giao dịch, hồ sơ tín dụng và tác động của lịch sale/lễ trên cùng một seed.</p>
            </div>
            <div className="date-range"><span className="calendar-icon">▦</span><span>{data.metadata.startDate} <b>→</b> {data.metadata.endDate}</span></div>
          </section>

          <section className="metric-grid" aria-label="Tổng quan dataset">
            <MetricCard label="Khách hàng" value={number.format(data.summary.customers)} foot={`${number.format(data.summary.accounts)} tài khoản`} />
            <MetricCard label="Giao dịch" value={number.format(data.summary.transactions)} foot={`${number.format(data.summary.events)} sự kiện`} />
            <MetricCard label="Giá trị trong tháng" value={money(selected?.amountTotalVnd ?? data.summary.amountTotalVnd)} foot={`${selected ? monthLabel(selected.month) : "Toàn kỳ"} · VND`} />
            <MetricCard label="Giao dịch bất thường" value={`${data.summary.anomalyRatePct.toFixed(2)}%`} foot={`${number.format(data.summary.anomalies)} nhãn · cấu hình 2%`} />
          </section>

          <section className="content-grid" id="traffic">
            <article className="panel traffic-panel">
              <div className="panel-heading">
                <div><div className="eyebrow">THEO THỜI GIAN</div><h2>Lưu lượng theo tháng</h2></div>
                <div className="segmented-control" role="group" aria-label="Chỉ số biểu đồ">
                  <button className={chartMode === "transactions" ? "selected" : ""} onClick={() => setChartMode("transactions")}>Số lượng</button>
                  <button className={chartMode === "amount" ? "selected" : ""} onClick={() => setChartMode("amount")}>Giá trị</button>
                </div>
              </div>
              <div className="chart-summary"><b>{selected ? (chartMode === "transactions" ? number.format(selected.transactions) : money(selected.amountTotalVnd)) : "—"}</b><span>{selected ? monthLabel(selected.month) : ""}</span>{selected?.dailyChangePct !== null && selected?.dailyChangePct !== undefined && <em className={selected.dailyChangePct >= 0 ? "positive" : "negative"}>{formatDelta(selected.dailyChangePct)} / ngày</em>}</div>
              <div className="bar-chart" role="img" aria-label="Biểu đồ lưu lượng giao dịch theo tháng">
                {data.monthlyTraffic.map((row) => {
                  const value = chartMode === "transactions" ? row.dailyAverage : row.amountTotalVnd;
                  const height = Math.max(6, (value / maxMonthly) * 100);
                  return <button className={`bar-column ${row.month === selected?.month ? "chosen" : ""}`} key={row.month} onClick={() => setSelectedMonth(row.month)} aria-label={`${monthLabel(row.month)}: ${number.format(row.transactions)} giao dịch`}>
                    <span className="bar-value">{chartMode === "transactions" ? row.dailyAverage.toFixed(1) : money(row.amountTotalVnd)}</span>
                    <span className="bar-track"><i style={{ height: `${height}%` }}/></span>
                    <span className="bar-month">{monthLabel(row.month)}</span>
                  </button>;
                })}
              </div>
              <div className="chart-footnote"><span><i className="legend-swatch"/> Dữ liệu mô phỏng</span><span>Trung bình/ngày đã chuẩn hóa theo độ dài tháng</span></div>
            </article>

            <article className="panel mix-panel">
              <div className="panel-heading"><div><div className="eyebrow">CƠ CẤU</div><h2>Loại giao dịch</h2></div></div>
              <div className="donut-wrap"><div className="donut" style={donutStyle}><div><b>{compact.format(typeTotal)}</b><span>giao dịch</span></div></div></div>
              <div className="legend-list">
                {transactionTypes.map((item, index) => <div className="legend-row" key={item.label}><span className={`legend-dot color-${index % 5}`}/><span>{prettyType(item.label)}</span><b>{(item.count / Math.max(typeTotal, 1) * 100).toFixed(1)}%</b><small>{number.format(item.count)}</small></div>)}
              </div>
            </article>
          </section>

          <section className="content-grid lower-grid" id="special-days">
            <article className="panel special-panel">
              <div className="panel-heading"><div><div className="eyebrow">ẢNH HƯỞNG LỊCH</div><h2>Ngày sale, lễ và ngày thường</h2></div><span className="comparison-pill">Ngày thường: mốc so sánh</span></div>
              <div className="special-list">
                {topCalendar.map((row) => <div className="special-row" key={row.tag}>
                  <div className="special-name"><span className={`special-type ${row.tag.startsWith("campaign") ? "campaign" : "holiday"}`}>{row.tag.startsWith("campaign") ? "Sale" : "Lễ"}</span><span><b>{tagLabel(row.tag)}</b><small>{row.days} {row.days === 1 ? "ngày" : "ngày trong kỳ"}</small></span></div>
                  <div className="special-bar"><i style={{ width: `${Math.min(100, Math.max(3, (row.transactionsPerDay / Math.max(...topCalendar.map((item) => item.transactionsPerDay))) * 100))}%` }}/></div>
                  <div className="special-count">{row.transactionsPerDay.toFixed(1)}<small>GD/ngày</small></div>
                  <div className={`impact ${row.transactionChangePct !== null && row.transactionChangePct >= 0 ? "positive" : "negative"}`}>{formatDelta(row.transactionChangePct)}</div>
                </div>)}
              </div>
              <p className="panel-note">* Hệ số ngày sale/lễ là giả định của generator, không phải thống kê thị trường thực tế.</p>
            </article>

            <article className="panel credit-panel">
              <div className="panel-heading"><div><div className="eyebrow">TÍN DỤNG & VAY</div><h2>Hồ sơ khách hàng</h2></div></div>
              <div className="profile-stat"><div className="profile-stat-icon">◈</div><div><small>Điểm tín dụng</small><b>{rangeValue(data, "Credit score")}</b><span>khoảng điểm quan sát được</span></div></div>
              <div className="profile-stat"><div className="profile-stat-icon sand">⌂</div><div><small>Khoản vay được duyệt</small><b>{number.format(data.summary.approvedApplications)} <em>/ {number.format(data.summary.customers)}</em></b><span>{(data.summary.approvedApplications / Math.max(data.summary.customers, 1) * 100).toFixed(1)}% hồ sơ</span></div><div className="approval-ring" style={{ "--progress": `${data.summary.approvedApplications / Math.max(data.summary.customers, 1) * 100}%` } as CSSProperties}><span>{Math.round(data.summary.approvedApplications / Math.max(data.summary.customers, 1) * 100)}%</span></div></div>
              <div className="credit-foot"><span>Gói vay</span><b>{number.format(data.categories.find((item) => item.name === "Loan package")?.values.length ?? 0)} sản phẩm</b><span>Khoản vay</span><b>{number.format(data.summary.loans)} hồ sơ</b></div>
            </article>
          </section>

          <section className="panel fields-panel" id="fields">
            <div className="panel-heading fields-heading"><div><div className="eyebrow">PHÂN BỐ DATA RANGE</div><h2>Phân bố {fieldLabel(selectedTrendField).toLocaleLowerCase()} theo tháng</h2><p>Các khoảng giá trị giữ cố định giữa các tháng để so sánh phân bố.</p></div><label className="field-select-label">Trường dữ liệu<select value={selectedTrendField} onChange={(event) => setTrendField(event.target.value)}>{trendFields.map((item) => <option key={item.field} value={item.field}>{fieldLabel(item.field)}</option>)}</select></label></div>
            <div className="histogram-scroll"><div className="field-histogram" style={{ "--month-count": histogramMonths.length } as CSSProperties}>
              <div className="histogram-axis"><span>Khoảng giá trị</span>{selectedHistogram?.bins.map((bin, index) => <b key={index}>{index === selectedHistogram.bins.length - 1 ? "≤ " : ""}{formatTrend(bin.min, selectedTrendField)}–{formatTrend(bin.max, selectedTrendField)}{index === selectedHistogram.bins.length - 1 ? " (bao gồm max)" : ""}</b>)}</div>
              {histogramMonths.map((month) => <div className="histogram-month" key={month}><b>{monthLabel(month)}</b>{selectedHistogram?.bins.map((bin, index) => { const count = bin.months[month] ?? 0; return <div className="histogram-cell" key={index} title={`${monthLabel(month)} · ${formatTrend(bin.min, selectedTrendField)}–${formatTrend(bin.max, selectedTrendField)} · ${number.format(count)} bản ghi`}><i style={{ width: `${count ? Math.max(3, count / maxHistogramCount * 100) : 0}%` }}/><span>{number.format(count)}</span></div>; })}</div>)}
            </div></div>
            <p className="field-trend-note">Mỗi ô cho biết số giao dịch trong tháng rơi vào khoảng giá trị đó. Cực đại toàn kỳ: {formatTrend(selectedHistogram?.max ?? 0, selectedTrendField)}.</p>
            <div className="panel-heading fields-heading field-table-heading"><div><div className="eyebrow">PHẠM VI GIÁ TRỊ</div><h2>Min–max theo trường</h2></div><label className="search-box"><span>⌕</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tìm theo tên hoặc field…" /></label></div>
            <div className="field-filters" aria-label="Nhóm trường dữ liệu">
              {[ ["all", "Tất cả"], ["customer", "Khách hàng"], ["account", "Tài khoản"], ["credit", "Tín dụng"], ["loan", "Khoản vay"], ["transaction", "Giao dịch"] ].map(([key, label]) => <button key={key} className={fieldGroup === key ? "active" : ""} onClick={() => setFieldGroup(key)}>{label}</button>)}
            </div>
            <div className="table-wrap"><table><thead><tr><th>TRƯỜNG</th><th>NHỎ NHẤT</th><th>LỚN NHẤT</th><th>ĐƠN VỊ</th></tr></thead><tbody>
              {filteredFields.map((item) => <tr key={item.field}><td><b>{fieldLabel(item.field)}</b><small>{fieldPath(item.field)}</small></td><td>{formatField(item.min)}</td><td>{formatField(item.max)}</td><td>{item.unit || "—"}</td></tr>)}
              {filteredFields.length === 0 && <tr><td colSpan={4} className="empty-row">Không tìm thấy trường phù hợp.</td></tr>}
            </tbody></table></div>
            <div className="table-footer">Đang hiển thị {filteredFields.length} / {data.fieldRanges.length} trường số</div>
          </section>

          <footer className="page-footer"><span>ANOMALY DATA PIPELINE</span><span>Seed {data.metadata.seed} · {data.metadata.sourceProfile} · Dữ liệu tổng hợp</span></footer>
        </div>
      </main>
    </div>
  );
}

function MetricCard({ label, value, foot }: { label: string; value: string; foot: string }) {
  return <article className="metric-card"><span className="metric-label">{label}</span><b className="metric-value">{value}</b><small>{foot}</small></article>;
}

function formatDelta(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function prettyType(value: string) {
  return ({ TRANSFER: "Chuyển khoản", CASH_OUT: "Rút tiền", CASH_IN: "Nạp tiền", PAYMENT: "Thanh toán", DEBIT: "Ghi nợ" } as Record<string, string>)[value] ?? value;
}

function tagLabel(value: string) {
  if (value.startsWith("campaign_")) return `Ngày sale ${value.slice(-4, -2)}/${value.slice(-2)}`;
  return tagNames[value] ?? value.replaceAll("_", " ");
}

function rangeValue(data: DashboardData, field: string) {
  const row = data.fieldRanges.find((item) => item.field === field);
  return row ? `${number.format(row.min)}–${number.format(row.max)}` : "—";
}

function formatField(value: number) {
  if (value >= 100_000) return number.format(value);
  return Number.isInteger(value) ? number.format(value) : value.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
}

function formatTrend(value: number, field: string) {
  if (field === "Transaction amount" || field === "Monthly income" || field === "Opening account balance") return money(value);
  return Number.isInteger(value) ? number.format(value) : value.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
}

function fieldLabel(field: string) {
  return ({
    "Age at simulation start": "Tuổi khách hàng",
    "Monthly income": "Thu nhập tháng",
    "Credit score": "Điểm tín dụng hiện tại",
    "Credit history score": "Điểm tín dụng lịch sử",
    "Opening account balance": "Số dư đầu kỳ",
    "Loan request": "Số tiền đề nghị vay",
    "Loan term": "Kỳ hạn vay",
    "Loan principal": "Gốc khoản vay",
    "Outstanding principal": "Dư nợ còn lại",
    "Loan interest rate": "Lãi suất khoản vay",
    "Transaction amount": "Số tiền giao dịch",
    "Risk score": "Điểm rủi ro",
  } as Record<string, string>)[field] ?? field;
}

function fieldPath(field: string) {
  return ({
    "Age at simulation start": "customers.profile.date_of_birth",
    "Monthly income": "customers.profile.demographics.monthly_income",
    "Credit score": "customers.credit_profile.score",
    "Credit history score": "customers.credit_profile.history.score",
    "Opening account balance": "accounts.balance.current",
    "Loan request": "loan_applications.request.amount",
    "Loan term": "loan_applications.request.term_months",
    "Loan principal": "loans.principal",
    "Outstanding principal": "loans.outstanding_principal",
    "Loan interest rate": "loans.interest_rate",
    "Transaction amount": "transactions.amount",
    "Risk score": "transactions.risk.score",
  } as Record<string, string>)[field] ?? field;
}

function fieldGroupFor(field: string) {
  if (field.startsWith("Credit")) return "credit";
  if (field.startsWith("Loan") || field === "Outstanding principal") return "loan";
  if (field === "Opening account balance") return "account";
  if (field === "Transaction amount" || field === "Risk score") return "transaction";
  return "customer";
}

export default App;
