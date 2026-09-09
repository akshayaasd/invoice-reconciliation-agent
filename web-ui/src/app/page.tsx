"use client";

import { useState, useEffect, useMemo } from "react";
import { AlertCircle, CheckCircle2, FileSpreadsheet, Send, Download, Search, ChevronLeft, ChevronRight, PieChart as PieChartIcon } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";

const PAGE_SIZE = 10;

export default function Dashboard() {
  const [metadata, setMetadata] = useState<any>(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditComplete, setAuditComplete] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [emailDraft, setEmailDraft] = useState("");
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailSent, setEmailSent] = useState(false);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  // Agentic thinking loop states
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const steps = [
    "Initializing audit agent...",
    "Extracting invoice and Sitetracker CSVs...",
    "Normalizing job references...",
    "Cross-referencing completion dates and PO lines...",
    "Evaluating discrepancies against business rules...",
    "Drafting dispute notice via LLM...",
    "Finalizing audit report...",
  ];

  // Helper: build CSV string from discrepancies array
  const buildCsv = (discrepancies: any[]) => {
    const headers = "job,work_item,status,rule,severity,billed,allowed,dollar_impact,original_ref";
    const rows = discrepancies.map((d: any) =>
      [d.job, d.work_item, d.status, `"${d.rule}"`, d.severity, d.billed, d.allowed, d.dollar_impact, d.original_ref].join(",")
    );
    return [headers, ...rows].join("\n");
  };

  useEffect(() => {
    fetch("http://localhost:8000/api/metadata")
      .then((res) => res.json())
      .then((data) => setMetadata(data))
      .catch(console.error);
  }, []);

  const runAudit = async () => {
    setIsAuditing(true);
    setAuditComplete(false);
    setCurrentStep(0);
    setCompletedSteps([]);
    setEmailSent(false);
    setPage(0);
    setSearch("");

    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => {
        setCompletedSteps((done) => (done.includes(prev) ? done : [...done, prev]));
        if (prev < steps.length - 1) return prev + 1;
        return prev;
      });
    }, 1200);

    try {
      const [res] = await Promise.all([
        fetch("http://localhost:8000/api/analyze", { method: "POST" }),
        new Promise((resolve) => setTimeout(resolve, 6000)),
      ]);

      const data = await (res as Response).json();

      clearInterval(stepInterval);
      setCompletedSteps(steps.map((_, i) => i)); // mark all done
      setResults(data);
      setEmailDraft(data.email_draft);
      setAuditComplete(true);
      setIsAuditing(false);
    } catch (e) {
      clearInterval(stepInterval);
      setIsAuditing(false);
      console.error(e);
      alert("Failed to connect to backend. Is it running on port 8000?");
    }
  };

  const sendEmail = async () => {
    setSendingEmail(true);
    try {
      const csvData = buildCsv(results.discrepancies);
      const res = await fetch("http://localhost:8000/api/send_email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email_body: emailDraft,
          invoice_no: metadata.invoice_no,
          csv_data: csvData,
          approval_token: results.approval_token,
          email_subject: results.email_subject
        }),
      });
      if (res.ok) setEmailSent(true);
    } catch (e) {
      console.error(e);
    } finally {
      setSendingEmail(false);
    }
  };

  const downloadCsv = () => {
    if (!results) return;
    const csv = buildCsv(results.discrepancies);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit_report_${metadata.invoice_no}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredDiscrepancies = results?.discrepancies?.filter((d: any) => {
    const q = search.toLowerCase();
    return (
      !q ||
      d.original_ref?.toLowerCase().includes(q) ||
      d.job?.toLowerCase().includes(q) ||
      d.work_item?.toLowerCase().includes(q) ||
      d.rule?.toLowerCase().includes(q) ||
      d.severity?.toLowerCase().includes(q)
    );
  });

  const chartData = useMemo(() => {
    if (!results) return { pie: [], bar: [] };
    
    const ruleImpacts: Record<string, number> = {};

    results.discrepancies.forEach((d: any) => {
      let genericRule = d.rule.split('.')[0];
      if (d.rule.startsWith("Status contradicts")) genericRule = "Status contradicts completion dates";
      
      if (!ruleImpacts[genericRule]) ruleImpacts[genericRule] = 0;
      ruleImpacts[genericRule] += d.dollar_impact;
    });

    const disputedAmount = results.summary_by_severity?.["Disputed"] || 0;
    const needsReviewAmount = results.summary_by_severity?.["Needs review"] || 0;
    const cleanAmount = 172929.50 - (disputedAmount + needsReviewAmount);

    const pie = [
      { name: "Clean", value: cleanAmount, color: "#10b981" }, // green-500
      { name: "Needs Review", value: needsReviewAmount, color: "#f59e0b" }, // amber-500
      { name: "Disputed", value: disputedAmount, color: "#ef4444" }, // red-500
    ];

    const bar = Object.keys(ruleImpacts).map(rule => ({
      rule: rule,
      fullRule: rule,
      impact: ruleImpacts[rule]
    })).sort((a, b) => b.impact - a.impact);

    return { pie, bar };
  }, [results]);

  if (!metadata)
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-12 w-12 rounded-full border-4 border-teal-500 border-t-transparent animate-spin mb-4"></div>
          <p className="text-gray-500 font-medium">Loading...</p>
        </div>
      </div>
    );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-5 flex flex-col md:flex-row md:items-center justify-between sticky top-0 z-10 shadow-sm gap-4">
        <div className="flex items-center gap-6">
          <img 
            src="https://www.sitetracker.com/wp-content/uploads/2022/06/Sitetracker-Logo-Approved-2022_rgb-fullcolor.svg" 
            alt="Sitetracker" 
            className="h-8" 
          />
          <div className="border-l border-gray-300 pl-6">
            <h1 className="text-xl font-bold text-gray-900">AI Invoice Auditor</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Reconcile subcontractor invoices against Sitetracker Job execution and PO data.
            </p>
          </div>
        </div>
        <button
          onClick={runAudit}
          disabled={isAuditing}
          className="bg-teal-600 hover:bg-teal-700 text-white px-6 py-2.5 rounded-lg font-medium transition-all shadow-sm flex items-center justify-center gap-3 disabled:opacity-90 disabled:cursor-wait whitespace-nowrap min-w-[280px]"
        >
          {isAuditing ? (
            <>
              <div className="h-5 w-5 border-2 border-teal-200 border-t-white rounded-full animate-spin"></div>
              <div className="flex flex-col items-start text-left">
                <span className="text-xs text-teal-200 font-semibold tracking-wider uppercase">Agent Executing</span>
                <span className="text-sm">{steps[currentStep]}</span>
              </div>
            </>
          ) : (
            <>🚀 {auditComplete ? "Rerun AI Audit" : "Run AI Audit"}</>
          )}
        </button>
      </header>

      <main className="flex-1 overflow-auto p-4 md:p-8">
        <div className="max-w-7xl mx-auto space-y-6">

          {/* Invoice context */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-wrap gap-x-12 gap-y-4">
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Vendor</p>
              <p className="text-sm font-medium text-gray-900 mt-1">{metadata.vendor}</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Invoice</p>
              <p className="text-sm font-medium text-gray-900 mt-1 flex items-center gap-1">
                <span className="bg-gray-100 px-2 py-0.5 rounded font-mono border border-gray-200">{metadata.invoice_no}</span>
                <span className="text-gray-500">($172,929.50)</span>
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Period</p>
              <p className="text-sm font-medium text-gray-900 mt-1">{metadata.period}</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">PO Reference</p>
              <p className="text-sm font-medium text-gray-900 mt-1">
                <span className="bg-gray-100 px-2 py-0.5 rounded font-mono border border-gray-200">{metadata.po_ref}</span>
              </p>
            </div>
          </div>

          {/* Agent log — only visible while auditing, disappears when results load */}
          {isAuditing && (
            <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 font-mono text-sm flex flex-col max-h-64 overflow-hidden">
              <div className="flex gap-2 mb-4 items-center">
                <div className="w-2.5 h-2.5 rounded-full bg-teal-400 animate-pulse"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-teal-300"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-teal-200"></div>
                <span className="ml-3 text-xs text-teal-600 uppercase font-bold tracking-widest">System Log</span>
              </div>
              <div className="overflow-y-auto space-y-2 flex-1">
                {steps.slice(0, currentStep + 1).map((step, i) => (
                  <div key={i} className="flex gap-3 items-center">
                    <span className="text-teal-500 shrink-0">➜</span>
                    <span className={completedSteps.includes(i) ? "text-gray-400" : "text-gray-800 font-medium"}>{step}</span>
                    {completedSteps.includes(i) && (
                      <span className="text-teal-500 ml-auto flex items-center gap-1 text-xs uppercase tracking-wider font-semibold">
                        <CheckCircle2 size={12} /> Done
                      </span>
                    )}
                    {!completedSteps.includes(i) && i === currentStep && (
                      <span className="text-teal-600 ml-auto flex items-center gap-1 text-xs uppercase tracking-wider font-semibold animate-pulse">Running...</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Results */}
          {auditComplete && results && (
            <div className="space-y-6">
              {/* KPIs */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm border-t-4 border-t-teal-500">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">Lines Audited</p>
                  <h3 className="text-3xl font-bold text-gray-900">{results.lines_audited}</h3>
                </div>
                <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm border-t-4 border-t-red-500">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">Discrepancies Flagged</p>
                  <h3 className="text-3xl font-bold text-gray-900">{results.discrepancies.length}</h3>
                </div>
                <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm border-t-4 border-t-green-600 bg-green-50/30">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-1">Total Exposure</p>
                  <h3 className="text-3xl font-bold text-green-700">
                    ${results.estimated_overbilling.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </h3>
                </div>
              </div>

              {/* Charts */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Pie Chart */}
                <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm lg:col-span-1 flex flex-col">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                    <PieChartIcon size={16} className="text-gray-400" /> Breakdown by Status
                  </p>
                  <div className="flex-1 w-full min-h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={chartData.pie} innerRadius={45} outerRadius={70} paddingAngle={2} dataKey="value" stroke="none">
                          {chartData.pie.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip 
                          formatter={(val: number) => `$${val.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`}
                          contentStyle={{ borderRadius: '8px', fontSize: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} 
                        />
                        <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Bar Chart */}
                <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm lg:col-span-2 flex flex-col">
                  <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                    <AlertCircle size={16} className="text-gray-400" /> Financial Impact by Rule
                  </p>
                  <div className="flex-1 w-full min-h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart layout="vertical" data={chartData.bar} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f3f4f6" />
                        <XAxis type="number" tickFormatter={(val) => `$${val/1000}k`} tick={{fontSize: 11, fill: '#9ca3af'}} axisLine={false} tickLine={false} />
                        <YAxis type="category" dataKey="rule" width={200} tick={{fontSize: 11, fill: '#6b7280'}} axisLine={false} tickLine={false} />
                        <Tooltip 
                          formatter={(val: number) => [`$${val.toLocaleString(undefined, {minimumFractionDigits: 2})}`, 'Impact']}
                          labelFormatter={(label, payload) => payload?.[0]?.payload?.fullRule || label}
                          contentStyle={{ borderRadius: '8px', fontSize: '12px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} 
                          labelStyle={{ color: '#374151', fontWeight: 500, paddingBottom: '4px' }}
                        />
                        <Bar dataKey="impact" fill="#0f766e" radius={[0, 4, 4, 0]} maxBarSize={30} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Audit table */}
                <div className="lg:col-span-7">
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex flex-col h-[580px]">
                    <div className="px-6 py-4 border-b border-gray-200 bg-gray-50/50 flex items-center justify-between gap-3">
                      <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2 shrink-0">
                        <FileSpreadsheet className="text-teal-600" size={20} />
                        Audit Report
                      </h2>
                      <div className="flex items-center gap-2 flex-1">
                        <div className="relative flex-1 max-w-xs">
                          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                          <input
                            type="text"
                            placeholder="Search job, rule, severity..."
                            value={search}
                            onChange={(e) => { setSearch(e.target.value); setPage(0); }}
                            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 outline-none"
                          />
                        </div>
                        <button
                          onClick={downloadCsv}
                          className="flex items-center gap-1.5 text-xs font-semibold text-teal-700 bg-teal-50 px-3 py-1.5 rounded-lg hover:bg-teal-100 transition-colors border border-teal-100 whitespace-nowrap"
                        >
                          <Download size={14} /> Download CSV
                        </button>
                      </div>
                    </div>

                    <div className="p-5 overflow-y-auto flex-1">
                      <div className="bg-red-50 text-red-900 p-4 rounded-lg mb-5 border border-red-100 flex gap-3 text-sm">
                        <AlertCircle className="shrink-0 text-red-500 mt-0.5" size={18} />
                        <div>
                          <strong>${results.disputed_overbilling.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>{" "}
                          of this <strong>$172,929.50</strong> invoice does not hold up —{" "}
                          <strong>{((results.disputed_overbilling / 172929.50) * 100).toFixed(1)}%</strong> is billing for work Sitetracker says has not happened.
                        </div>
                      </div>

                      <div className="border border-gray-200 rounded-lg overflow-hidden">
                        <table className="w-full text-left text-sm">
                          <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 uppercase text-xs tracking-wider">
                            <tr>
                              <th className="px-4 py-3 font-medium whitespace-nowrap">Job Ref</th>
                              <th className="px-4 py-3 font-medium whitespace-nowrap">Work Item</th>
                              <th className="px-4 py-3 font-medium whitespace-nowrap">Status</th>
                              <th className="px-4 py-3 font-medium whitespace-nowrap">Severity</th>
                              <th className="px-4 py-3 font-medium whitespace-nowrap">Impact</th>
                              <th className="px-4 py-3 font-medium">Rule</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200 bg-white">
                            {filteredDiscrepancies?.length === 0 ? (
                              <tr>
                                <td colSpan={5} className="px-4 py-8 text-center text-gray-400 text-sm">No results match your search.</td>
                              </tr>
                            ) : (
                              filteredDiscrepancies?.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE).map((d: any, i: number) => (
                                <tr key={i} className="hover:bg-gray-50 transition-colors">
                                  <td className="px-4 py-3 font-mono text-gray-600 whitespace-nowrap">{d.original_ref}</td>
                                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">{d.work_item}</td>
                                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap text-xs font-medium">{d.status}</td>
                                  <td className="px-4 py-3 whitespace-nowrap">
                                    <span className={`px-2 py-1 rounded text-xs font-semibold ${d.severity === "Disputed" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-800"}`}>
                                      {d.severity}
                                    </span>
                                  </td>
                                  <td className="px-4 py-3 font-semibold text-gray-900 whitespace-nowrap">
                                    ${d.dollar_impact.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                  </td>
                                  <td className="px-4 py-3 text-gray-500 text-xs max-w-[220px]" title={d.rule}>
                                    {d.rule}
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>

                      {/* Pagination footer */}
                      {filteredDiscrepancies && filteredDiscrepancies.length > PAGE_SIZE && (
                        <div className="flex items-center justify-between mt-3 px-1">
                          <p className="text-xs text-gray-400">
                            Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, filteredDiscrepancies.length)} of {filteredDiscrepancies.length}
                          </p>
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => setPage(p => Math.max(0, p - 1))}
                              disabled={page === 0}
                              className="p-1.5 rounded border border-gray-200 text-gray-500 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            >
                              <ChevronLeft size={14} />
                            </button>
                            <span className="text-xs text-gray-500 px-2 font-medium">Page {page + 1} / {Math.ceil(filteredDiscrepancies.length / PAGE_SIZE)}</span>
                            <button
                              onClick={() => setPage(p => Math.min(Math.ceil(filteredDiscrepancies.length / PAGE_SIZE) - 1, p + 1))}
                              disabled={(page + 1) * PAGE_SIZE >= filteredDiscrepancies.length}
                              className="p-1.5 rounded border border-gray-200 text-gray-500 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                            >
                              <ChevronRight size={14} />
                            </button>
                          </div>
                        </div>
                      )}
                      {search && filteredDiscrepancies && (
                        <p className="text-xs text-gray-400 mt-2 pl-1">
                          {filteredDiscrepancies.length} of {results.discrepancies.length} rows match "{search}"
                        </p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Email panel */}
                <div className="lg:col-span-5">
                  <div className="bg-white rounded-xl border border-gray-200 shadow-sm flex flex-col h-[580px] overflow-hidden">
                    <div className="px-6 py-4 border-b border-gray-200 bg-gray-50/50">
                      <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                        <Send className="text-teal-600" size={20} />
                        Vendor Communication
                      </h2>
                    </div>

                    <div className="p-6 flex-1 flex flex-col">
                      <div className="bg-teal-50 text-teal-800 p-3 rounded-lg mb-4 text-sm border border-teal-100 flex gap-2 items-start">
                        <span className="shrink-0 mt-0.5">✨</span>
                        <p>AI-drafted dispute notice based on audit. <strong>Human approval required before sending.</strong></p>
                      </div>

                      <label className="text-sm font-semibold text-gray-700 mb-1 block">Review & Edit Draft:</label>
                      <textarea
                        className="flex-1 w-full border border-gray-300 rounded-lg p-4 text-sm text-gray-700 focus:ring-2 focus:ring-teal-500 focus:border-teal-500 transition-all font-mono resize-none bg-gray-50 shadow-inner"
                        value={emailDraft}
                        onChange={(e) => setEmailDraft(e.target.value)}
                      />

                      <div className="mt-3 text-xs text-gray-500 flex items-center gap-1.5 bg-gray-50 p-2 rounded border border-gray-100">
                        <span className="font-medium bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded">📎</span>
                        audit_report_{metadata.invoice_no}.csv — {results.discrepancies.length} rows attached
                      </div>
                    </div>

                    <div className="p-4 border-t border-gray-200 bg-gray-50">
                      {!emailSent ? (
                        <button
                          onClick={sendEmail}
                          disabled={sendingEmail}
                          className="w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-3.5 px-4 rounded-lg flex justify-center items-center gap-2 transition-colors disabled:opacity-70 shadow-sm text-base"
                        >
                          {sendingEmail ? (
                            <><div className="h-5 w-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div> Sending via Resend...</>
                          ) : (
                            <>Approve & Send to Vendor</>
                          )}
                        </button>
                      ) : (
                        <div className="w-full bg-green-100 border border-green-200 text-green-800 font-bold py-3.5 px-4 rounded-lg flex justify-center items-center gap-2 shadow-sm text-base">
                          <CheckCircle2 size={20} /> Email Dispatched Successfully!
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
