import { useState } from "react";
import { api } from "../../api/client";

export default function RealCheckoutForm() {
  const [rows, setRows] = useState([
    { name: "", email: "", phone: "", amount: "", record_type: "payment" },
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [links, setLinks] = useState([]);
  const [error, setError] = useState(null);

  const updateRow = (i, field, value) => {
    const updated = [...rows];
    updated[i][field] = value;
    setRows(updated);
  };

  const addRow = () => {
    setRows([...rows, { name: "", email: "", phone: "", amount: "", record_type: "payment" }]);
  };

  const removeRow = (i) => setRows(rows.filter((_, idx) => idx !== i));

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    setLinks([]);

    try {
      const results = [];
      for (const row of rows) {
        if (!row.name || !row.email || !row.phone || !row.amount) continue;

        const res = await api.post("/checkout/create", {
          name: row.name,
          email: row.email,
          phone: row.phone,
          amount: parseFloat(row.amount),
          record_type: row.record_type,
        });

        results.push({
          name: row.name,
          amount: row.amount,
          url: `${api.defaults.baseURL}${res.data.checkout_url}`,
          transaction_id: res.data.transaction_id,
        });
      }
      setLinks(results);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to create checkout session(s)");
    }

    setSubmitting(false);
  };

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-2">Real Checkout — Capture Genuine Failures</h3>
      <p className="text-raahi-muted text-xs mb-4">
        Enter real customer details. RAAHI creates a real Razorpay order and checkout page.
        Complete or fail the payment there — the real failure reason (from Razorpay's own
        webhook) becomes the genuine root cause RAAHI diagnoses, not a manual guess.
      </p>

      <div className="space-y-3 max-h-72 overflow-y-auto mb-4">
        {rows.map((row, i) => (
          <div key={i} className="grid grid-cols-6 gap-2 items-center bg-black/20 p-2 rounded-lg">
            <input
              placeholder="Name"
              value={row.name}
              onChange={(e) => updateRow(i, "name", e.target.value)}
              className="bg-raahi-bg text-raahi-text text-xs p-2 rounded col-span-1"
            />
            <input
              placeholder="Email"
              value={row.email}
              onChange={(e) => updateRow(i, "email", e.target.value)}
              className="bg-raahi-bg text-raahi-text text-xs p-2 rounded col-span-1"
            />
            <input
              placeholder="+91..."
              value={row.phone}
              onChange={(e) => updateRow(i, "phone", e.target.value)}
              className="bg-raahi-bg text-raahi-text text-xs p-2 rounded col-span-1"
            />
            <input
              placeholder="Amount"
              type="number"
              value={row.amount}
              onChange={(e) => updateRow(i, "amount", e.target.value)}
              className="bg-raahi-bg text-raahi-text text-xs p-2 rounded col-span-1"
            />
            <select
              value={row.record_type}
              onChange={(e) => updateRow(i, "record_type", e.target.value)}
              className="bg-raahi-bg text-raahi-text text-xs p-2 rounded col-span-1"
            >
              <option value="payment">Payment</option>
              <option value="subscription">Subscription</option>
              <option value="invoice">Invoice</option>
            </select>
            <button onClick={() => removeRow(i)} className="text-raahi-danger text-xs">
              ✕
            </button>
          </div>
        ))}
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={addRow}
          className="bg-black/30 text-raahi-text text-sm px-3 py-2 rounded-lg"
        >
          + Add Customer
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="bg-raahi-accent text-black font-semibold text-sm px-4 py-2 rounded-lg disabled:opacity-50"
        >
          {submitting ? "Creating checkout sessions..." : "Generate Real Checkout Links"}
        </button>
      </div>

      {error && <div className="text-raahi-danger text-sm mb-3">❌ {error}</div>}

      {links.length > 0 && (
        <div className="space-y-2">
          <div className="text-raahi-muted text-xs mb-1">
            Open each link and complete or fail the payment using a Razorpay test card:
          </div>
          {links.map((link, i) => (
            <div key={i} className="bg-black/20 rounded-lg p-2 flex justify-between items-center">
              <span className="text-raahi-text text-sm">
                {link.name} — ₹{parseFloat(link.amount).toLocaleString("en-IN")}
              </span>
              <a
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-raahi-accent text-sm underline"
              >
                Open Checkout →
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}