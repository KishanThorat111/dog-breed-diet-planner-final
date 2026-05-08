"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface NutritionChartProps {
  protein: number;
  fat: number;
  carbs: number;
}

const COLORS = ["#3b82f6", "#f59e0b", "#10b981"];

export function NutritionChart({ protein, fat, carbs }: NutritionChartProps) {
  const total = protein + fat + carbs;
  if (total === 0) return null;

  const data = [
    { name: "Protein", value: Math.round((protein / total) * 100) },
    { name: "Fat", value: Math.round((fat / total) * 100) },
    { name: "Carbs", value: Math.round((carbs / total) * 100) },
  ];

  return (
    <div className="h-40">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={42}
            outerRadius={60}
            dataKey="value"
            strokeWidth={0}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => [`${value}%`]}
            contentStyle={{
              background: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          />
          <Legend iconType="circle" iconSize={8} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
