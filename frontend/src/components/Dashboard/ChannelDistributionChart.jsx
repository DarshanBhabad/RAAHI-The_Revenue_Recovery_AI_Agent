import { useEffect, useState } from "react";
import { api } from "../../api/client";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

const COLORS = ["#22c55e", "#f59e0b", "#3b82f6", "#8b5cf6", "#ef4444"];

export default function ChannelDistributionChart() {
  const [data, setData] = useState([]);

  useEffect(() => {
    api.get("/dashboard/channel-distribution").then(r => {
      setData(Object.entries(r.data).map(([name, value]) => ({ name, value })));
    });
  }, []);

  if (data.length === 0) return null;

  return (
    <div className="bg-raahi-card rounded-xl p-4 border border-white/5">
      <h3 className="text-raahi-text font-semibold mb-3">Channel Distribution</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Pie>
          <Tooltip contentStyle={{ backgroundColor: "#131922", border: "1px solid #333" }} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}