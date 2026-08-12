import { LineChart, Line, ResponsiveContainer } from 'recharts'

interface SparklineChartProps {
  data: number[]
  /** Hex color used when `positive` prop is undefined */
  color?: string
  width?: number
  height?: number
  /**
   * Override line color:
   * - true  → gain green (#00C851)
   * - false → loss red  (#FF4444)
   * - undefined → use `color` prop
   */
  positive?: boolean
}

export function SparklineChart({
  data,
  color = '#6366f1',
  width = 80,
  height = 32,
  positive,
}: SparklineChartProps) {
  const lineColor =
    positive === true
      ? '#00C851'
      : positive === false
        ? '#FF4444'
        : color

  // Recharts requires objects; map raw numbers to { v: n }
  const chartData = data.map((v) => ({ v }))

  return (
    <ResponsiveContainer width={width} height={height}>
      <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
        <Line
          type="monotone"
          dataKey="v"
          stroke={lineColor}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
