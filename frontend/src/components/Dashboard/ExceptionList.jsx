export default function ExceptionList({ exceptions, onSelect }) {
  const isRealCheckout = (id) => id.startsWith("pending_") || id.includes("real");

  return (
    <div className="bg-raahi-card rounded-xl p-4 shadow-lg border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-4">
        Exceptions — Needs Human Review ({exceptions.length})
      </h3>
      <div className="space-y-2 max-h-80 overflow-y-auto">
        {exceptions.map((e) => (
          <button
            key={e.id}
            onClick={() => onSelect(e.id)}
            className="w-full text-left bg-black/20 hover:bg-black/40 rounded-lg p-3 transition"
          >
            <div className="flex justify-between">
              <span className="text-raahi-text text-sm font-medium">
                {e.id}
                {isRealCheckout(e.id) && (
                  <span className="bg-raahi-accent/20 text-raahi-accent text-[10px] px-1.5 py-0.5 rounded ml-2">
                    REAL CHECKOUT
                  </span>
                )}
              </span>
              <span className="text-raahi-danger text-sm">₹{e.amount.toLocaleString("en-IN")}</span>
            </div>
            <div className="text-raahi-muted text-xs mt-1">{e.exception_reason}</div>
          </button>
        ))}
      </div>
    </div>
  );
}