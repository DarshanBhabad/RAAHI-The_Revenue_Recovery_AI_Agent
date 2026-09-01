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
    <div className="flex gap-2 mb-4 flex-wrap">
      <button
        onClick={() => onChange(null)}
        className={`text-xs px-3 py-1.5 rounded-lg ${
          !selected ? "bg-raahi-accent text-black font-semibold" : "bg-black/30 text-raahi-muted"
        }`}
      >
        All Merchants
      </button>
      {merchants.map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          className={`text-xs px-3 py-1.5 rounded-lg ${
            selected === m ? "bg-raahi-accent text-black font-semibold" : "bg-black/30 text-raahi-muted"
          }`}
        >
          {DISPLAY_NAMES[m] || m}
        </button>
      ))}
    </div>
  );
}