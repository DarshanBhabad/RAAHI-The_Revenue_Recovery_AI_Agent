export default function ChatMockup({ customerName = "Priya Sharma", amount = 2499, dueDays = 15 }) {
  const messages = [
    {
      from: "raahi",
      text: `Namaste ${customerName} ji! 🙏 Aapka payment of ₹${amount.toLocaleString("en-IN")} ${dueDays} din se pending hai. Kya aap ise aaj complete kar sakte hain?`,
      time: "10:32 AM",
    },
    {
      from: "raahi",
      text: "Yahan click karke turant pay karein 👇",
      time: "10:32 AM",
    },
    {
      from: "raahi",
      text: "🔗 rzp.io/l/xyz123",
      time: "10:32 AM",
      isLink: true,
    },
    {
      from: "customer",
      text: "Haan bhai, kal tak kar dunga. Thoda busy hoon aaj.",
      time: "11:15 AM",
    },
    {
      from: "raahi",
      text: "Bilkul, koi baat nahi! Main aapko kal reminder bhej dunga. Dhanyavaad 😊",
      time: "11:16 AM",
    },
    {
      from: "system",
      text: "✅ Promise-to-pay logged — follow-up scheduled for tomorrow, 10:00 AM",
      time: "11:16 AM",
    },
  ];

  return (
    <div className="bg-raahi-card rounded-xl overflow-hidden border border-white/5 shadow-lg max-w-sm mx-auto">
      <div className="bg-green-700 px-4 py-3 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-white/20 flex items-center justify-center text-white font-semibold">
          R
        </div>
        <div>
          <div className="text-white font-medium text-sm">RAAHI Recovery Assistant</div>
          <div className="text-green-100 text-xs">online</div>
        </div>
      </div>

      <div
        className="p-4 space-y-3 min-h-[420px]"
        style={{
          backgroundColor: "#0b141a",
          backgroundImage:
            "radial-gradient(circle at 20px 20px, rgba(255,255,255,0.02) 1px, transparent 0)",
          backgroundSize: "20px 20px",
        }}
      >
        {messages.map((m, i) => {
          if (m.from === "system") {
            return (
              <div key={i} className="flex justify-center">
                <span className="bg-black/40 text-raahi-muted text-xs px-3 py-1 rounded-full">
                  {m.text}
                </span>
              </div>
            );
          }

          const isRaahi = m.from === "raahi";
          return (
            <div key={i} className={`flex ${isRaahi ? "justify-start" : "justify-end"}`}>
              <div
                className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                  isRaahi ? "bg-[#202c33] text-raahi-text" : "bg-[#005c4b] text-white"
                }`}
              >
                <div className={m.isLink ? "text-blue-400 underline" : ""}>{m.text}</div>
                <div className="text-[10px] text-white/50 text-right mt-1">{m.time}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}