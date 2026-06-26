import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { motion } from "framer-motion";

const COLORS = ["#dc2626", "#f59e0b", "#eab308", "#3b82f6", "#6b7280"];
const DEFAULT_DATA = [
  { name: "Critical", value: 2 },
  { name: "High", value: 5 },
  { name: "Medium", value: 8 },
  { name: "Low", value: 12 },
  { name: "Info", value: 3 },
];

export function FindingsPieChart({ findingsData }) {
  const data = findingsData && findingsData.length > 0 ? findingsData : DEFAULT_DATA;

  return (
    <motion.div
      className="chart-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
    >
      <h3>Findings by Severity</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={3}
            dataKey="value"
            animationDuration={1200}
            animationBegin={200}
          >
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} stroke="var(--surface)" strokeWidth={2} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 8,
              color: "var(--ink)",
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 11, color: "var(--ink-soft)" }}
            iconType="circle"
            iconSize={8}
          />
        </PieChart>
      </ResponsiveContainer>
    </motion.div>
  );
}
