import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { QueryStep } from '../types';

interface Props {
  step: QueryStep;
}

const PALETTE = ['#0E7C73', '#0A5A54', '#0E9F6E', '#3B82F6', '#8493A8'];

export default function ChartView({ step }: Props) {
  const [labelKey, valueKey] = step.columns;

  const data = step.rows.map((row) => ({
    label: String(row[labelKey] ?? '—'),
    value: Number(row[valueKey]),
  }));

  return (
    <div className="rounded-lg border border-line bg-surface p-3">
      <ResponsiveContainer width="100%" height={Math.max(180, data.length * 34)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
          barCategoryGap={6}
        >
          <CartesianGrid horizontal={false} stroke="#E3E9F0" />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: '#5B6B82', fontFamily: 'IBM Plex Mono' }}
            stroke="#CBD5E1"
          />
          <YAxis
            type="category"
            dataKey="label"
            width={140}
            tick={{ fontSize: 11, fill: '#2B3A4F', fontFamily: 'IBM Plex Sans' }}
            stroke="#CBD5E1"
          />
          <Tooltip
            cursor={{ fill: 'rgba(14, 124, 115, 0.06)' }}
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #E3E9F0',
              fontFamily: 'IBM Plex Mono',
              fontSize: 12,
            }}
            formatter={(v: number) => [v.toLocaleString(), valueKey]}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} isAnimationActive={false}>
            {data.map((_, i) => (
              <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
