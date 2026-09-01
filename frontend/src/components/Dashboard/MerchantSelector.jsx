import { useEffect, useState } from "react";
import { getMerchantList } from "../../api/client";

const DISPLAY_NAMES = {
  merch_d2c_001_raahi: "Urban Threads (D2C Fashion)",
  merch_saas_001_raahi: "Flowdesk (SaaS Subscription)",
  merch_b2b_001_raahi: "Bharat Supplies Co (B2B Wholesale)",
  merch_real_001: "Real Checkout Customers",
};

export default function MerchantSelector({ selected, onChange }) {
  const [merchants, setMerchants] = useState([]);

  useEffect(() => {
    getMerchantList().then(setMerchants);
  }, []);

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-raahi-muted text-xs hidden md:block">Filter:</span>
      <button
        onClick={() => onChange(null)}
        className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
          !selected
            ? "bg-raahi-accent text-black font-semibold border-raahi-accent"
            : "bg-transparent text-raahi-muted border-white/10 hover:text-raahi-text hover:border-white/20"
        }`}
      >
        All Merchants
      </button>
      {merchants.map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
            selected === m
              ? "bg-raahi-accent text-black font-semibold border-raahi-accent"
              : "bg-transparent text-raahi-muted border-white/10 hover:text-raahi-text hover:border-white/20"
          }`}
        >
          {DISPLAY_NAMES[m] || m}
        </button>
      ))}
    </div>
  );
}