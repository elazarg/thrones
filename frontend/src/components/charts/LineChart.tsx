import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface LineConfig {
  key: string;
  color: string;
  name: string;
}

interface LineChartProps {
  data: Array<Record<string, number>>;
  xKey: string;
  lines: LineConfig[];
  xLabel?: string;
  yLabel?: string;
  height?: number;
}

export function LineChart({
  data,
  xKey,
  lines,
  xLabel,
  yLabel,
  height = 180,
}: LineChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RechartsLineChart
        data={data}
        margin={{ top: 5, right: 10, bottom: xLabel ? 20 : 5, left: yLabel ? 30 : 0 }}
      >
        <XAxis
          dataKey={xKey}
          label={xLabel ? { value: xLabel, position: 'bottom', offset: 0, fontSize: 10, fill: '#8b949e' } : undefined}
          tick={{ fontSize: 9, fill: '#8b949e' }}
          tickFormatter={(v) => typeof v === 'number' ? v.toFixed(2) : v}
        />
        <YAxis
          label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', fontSize: 10, fill: '#8b949e' } : undefined}
          tick={{ fontSize: 9, fill: '#8b949e' }}
          domain={[0, 'auto']}
          tickFormatter={(v) => typeof v === 'number' ? (v < 0.01 ? v.toExponential(1) : v.toFixed(2)) : v}
        />
        <Tooltip
          contentStyle={{
            background: '#161b22',
            border: '1px solid #30363d',
            borderRadius: 6,
            fontSize: 11,
          }}
          formatter={(value: number) => value.toFixed(4)}
        />
        <Legend
          wrapperStyle={{ fontSize: 10, paddingTop: 4 }}
          iconSize={8}
        />
        {lines.map((line) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            stroke={line.color}
            name={line.name}
            dot={false}
            strokeWidth={1.5}
          />
        ))}
      </RechartsLineChart>
    </ResponsiveContainer>
  );
}
