import { useEffect, useRef, useState, useCallback } from 'react'
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type HistogramData,
  type LineData,
  type Time,
  type SeriesType,
} from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import { getChart, type OHLCV } from '@/api/market'
import { cn } from '@/lib/utils'
import { formatCurrency, formatCompact } from '@/lib/formatters'

// ─── Types ───────────────────────────────────────────────────────────────────

interface CandlestickChartProps {
  ticker: string
  height?: number
  className?: string
  disabled?: boolean
  /** Called whenever the chart data loads for a period with the period label
   *  and the period % return: (lastClose - firstOpen) / firstOpen * 100 */
  onPeriodChange?: (range: TimeRange, periodPct: number) => void
}

type TimeRange = '1D' | '1W' | '1M' | '3M' | '1Y'

interface CrosshairData {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

// ─── Period / interval mapping ────────────────────────────────────────────────

const RANGE_CONFIG: Record<TimeRange, { period: string; interval: string }> = {
  '1D': { period: '1d', interval: '5m' },
  '1W': { period: '5d', interval: '15m' },
  '1M': { period: '1mo', interval: '1d' },
  '3M': { period: '3mo', interval: '1d' },
  '1Y': { period: '1y', interval: '1wk' },
}

// ─── Theme constants ──────────────────────────────────────────────────────────

const COLORS = {
  bg: '#0a0e1a',
  bgPane: '#111827',
  border: '#1f2d40',
  text: '#94a3b8',
  gain: '#00C851',
  loss: '#FF4444',
  brand: '#6366f1',
  gainAlpha: 'rgba(0, 200, 81, 0.35)',
  lossAlpha: 'rgba(255, 68, 68, 0.35)',
  grid: '#1f2d40',
}

const CHART_BASE_OPTIONS = {
  layout: {
    background: { type: ColorType.Solid, color: COLORS.bg },
    textColor: COLORS.text,
    fontFamily: 'Inter, system-ui, sans-serif',
    fontSize: 11,
  },
  grid: {
    vertLines: { color: COLORS.grid, style: LineStyle.Solid },
    horzLines: { color: COLORS.grid, style: LineStyle.Solid },
  },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: { color: COLORS.brand, style: LineStyle.Dashed, width: 1 as const, labelBackgroundColor: COLORS.brand },
    horzLine: { color: COLORS.brand, style: LineStyle.Dashed, width: 1 as const, labelBackgroundColor: COLORS.brand },
  },
  rightPriceScale: { borderColor: COLORS.border },
  timeScale: { borderColor: COLORS.border, timeVisible: true, secondsVisible: false },
  handleScroll: true,
  handleScale: true,
}

// ─── Indicator calculations ───────────────────────────────────────────────────

function calcEMA(values: number[], period: number): number[] {
  const k = 2 / (period + 1)
  const result: number[] = []
  let ema = values[0]
  result.push(ema)
  for (let i = 1; i < values.length; i++) {
    ema = values[i] * k + ema * (1 - k)
    result.push(ema)
  }
  return result
}

function calcSMA(values: number[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) { result.push(null); continue }
    const slice = values.slice(i - period + 1, i + 1)
    result.push(slice.reduce((a, b) => a + b, 0) / period)
  }
  return result
}

function calcRSI(closes: number[], period = 14): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < period; i++) result.push(null)

  let avgGain = 0
  let avgLoss = 0
  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1]
    if (diff > 0) avgGain += diff
    else avgLoss -= diff
  }
  avgGain /= period
  avgLoss /= period

  const firstRsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
  result.push(firstRsi)

  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1]
    const gain = diff > 0 ? diff : 0
    const loss = diff < 0 ? -diff : 0
    avgGain = (avgGain * (period - 1) + gain) / period
    avgLoss = (avgLoss * (period - 1) + loss) / period
    const rsi = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss)
    result.push(rsi)
  }
  return result
}

function calcMACD(closes: number[]): {
  macd: (number | null)[]
  signal: (number | null)[]
  histogram: (number | null)[]
} {
  if (closes.length < 26) {
    const empty = closes.map(() => null)
    return { macd: empty, signal: empty, histogram: empty }
  }
  const ema12 = calcEMA(closes, 12)
  const ema26 = calcEMA(closes, 26)
  const macdLine = ema12.map((v, i) => v - ema26[i])

  // Signal is EMA(9) of MACD; first 25 points are undefined (EMA26 warmup)
  const validMacd = macdLine.slice(25)
  const signalRaw = calcEMA(validMacd, 9)

  const macd: (number | null)[] = macdLine.map((v, i) => (i >= 25 ? v : null))
  const signal: (number | null)[] = macdLine.map((_, i) => {
    if (i < 25) return null
    const si = i - 25
    return si < signalRaw.length ? signalRaw[si] : null
  })
  const histogram = macd.map((m, i) => {
    const s = signal[i]
    return m !== null && s !== null ? m - s : null
  })
  return { macd, signal, histogram }
}

function calcBollingerBands(closes: number[], period = 20): {
  upper: (number | null)[]
  middle: (number | null)[]
  lower: (number | null)[]
} {
  const middle = calcSMA(closes, period)
  const upper: (number | null)[] = []
  const lower: (number | null)[] = []

  for (let i = 0; i < closes.length; i++) {
    if (middle[i] === null) { upper.push(null); lower.push(null); continue }
    const slice = closes.slice(i - period + 1, i + 1)
    const mean = middle[i] as number
    const variance = slice.reduce((a, b) => a + (b - mean) ** 2, 0) / period
    const std = Math.sqrt(variance)
    upper.push(mean + 2 * std)
    lower.push(mean - 2 * std)
  }
  return { upper, middle, lower }
}

// ─── Helper: convert OHLCV → lightweight-charts data ─────────────────────────

function toUnixTime(iso: string): Time {
  return (new Date(iso).getTime() / 1000) as Time
}

function buildCandleData(data: OHLCV[]): CandlestickData[] {
  return data.map((d) => ({
    time: toUnixTime(d.timestamp),
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
  }))
}

function buildVolumeData(data: OHLCV[]): HistogramData[] {
  return data.map((d) => ({
    time: toUnixTime(d.timestamp),
    value: d.volume,
    color: d.close >= d.open ? COLORS.gainAlpha : COLORS.lossAlpha,
  }))
}

function buildLineData(times: Time[], values: (number | null)[]): LineData[] {
  return times
    .map((t, i) => (values[i] !== null ? { time: t, value: values[i] as number } : null))
    .filter(Boolean) as LineData[]
}

function buildHistogramData(
  times: Time[],
  values: (number | null)[],
): HistogramData[] {
  return times
    .map((t, i) => {
      const v = values[i]
      if (v === null) return null
      return { time: t, value: v, color: v >= 0 ? COLORS.gainAlpha : COLORS.lossAlpha }
    })
    .filter(Boolean) as HistogramData[]
}

// ─── Sub-component: indicator pane chart ─────────────────────────────────────

interface PaneChartHandle {
  chart: IChartApi
  container: HTMLDivElement
}

function createPaneChart(container: HTMLDivElement, paneHeight: number): IChartApi {
  return createChart(container, {
    ...CHART_BASE_OPTIONS,
    width: container.clientWidth,
    height: paneHeight,
    layout: {
      ...CHART_BASE_OPTIONS.layout,
      background: { type: ColorType.Solid, color: COLORS.bgPane },
    },
    rightPriceScale: { borderColor: COLORS.border, scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: { ...CHART_BASE_OPTIONS.timeScale, visible: false },
  })
}

// ─── Main component ───────────────────────────────────────────────────────────

export function CandlestickChart({
  ticker,
  height = 400,
  className,
  disabled = false,
  onPeriodChange,
}: CandlestickChartProps) {
  const [range, setRange] = useState<TimeRange>('1M')
  const [showBB, setShowBB] = useState(false)
  const [showRSI, setShowRSI] = useState(false)
  const [showMACD, setShowMACD] = useState(false)
  const [tooltip, setTooltip] = useState<CrosshairData | null>(null)

  // DOM refs
  const mainRef = useRef<HTMLDivElement>(null)
  const rsiRef = useRef<HTMLDivElement>(null)
  const macdRef = useRef<HTMLDivElement>(null)

  // Chart instance refs (not React state – we don't want re-renders on mutation)
  const mainChart = useRef<IChartApi | null>(null)
  const rsiChartRef = useRef<PaneChartHandle | null>(null)
  const macdChartRef = useRef<PaneChartHandle | null>(null)

  // Series refs
  const candleSeries = useRef<ISeriesApi<SeriesType> | null>(null)
  const volumeSeries = useRef<ISeriesApi<SeriesType> | null>(null)
  const bbUpperRef = useRef<ISeriesApi<SeriesType> | null>(null)
  const bbMiddleRef = useRef<ISeriesApi<SeriesType> | null>(null)
  const bbLowerRef = useRef<ISeriesApi<SeriesType> | null>(null)

  // ─ Fetch chart data ──────────────────────────────────────────────────────

  const { period, interval } = RANGE_CONFIG[range]
  const { data: chartData, isLoading, isError } = useQuery({
    queryKey: ['market', 'chart', ticker, period, interval],
    queryFn: () => getChart(ticker, period, interval),
    staleTime: 60_000,
    enabled: !disabled && ticker.length > 0,
  })

  // ─ Emit period % change to parent whenever chart data or range changes ────
  // Calculates (last close − first open) / first open × 100 so the parent
  // can display the correct return for the selected period (1D, 1W, 1M…).
  useEffect(() => {
    if (!onPeriodChange || !chartData?.data?.length) return
    const bars = chartData.data
    const firstOpen = bars[0].open
    const lastClose = bars[bars.length - 1].close
    if (!firstOpen || firstOpen === 0) return
    const pct = ((lastClose - firstOpen) / firstOpen) * 100
    onPeriodChange(range, pct)
  }, [chartData, range, onPeriodChange])

  // ─ Cleanup helper ────────────────────────────────────────────────────────

  const destroyCharts = useCallback(() => {
    try { mainChart.current?.remove() } catch { /* ignore */ }
    try { rsiChartRef.current?.chart.remove() } catch { /* ignore */ }
    try { macdChartRef.current?.chart.remove() } catch { /* ignore */ }
    mainChart.current = null
    candleSeries.current = null
    volumeSeries.current = null
    bbUpperRef.current = null
    bbMiddleRef.current = null
    bbLowerRef.current = null
    rsiChartRef.current = null
    macdChartRef.current = null
  }, [])

  // ─ Build / rebuild main chart ────────────────────────────────────────────

  useEffect(() => {
    if (!mainRef.current || !chartData?.data?.length) return

    destroyCharts()

    const container = mainRef.current
    const chart = createChart(container, {
      ...CHART_BASE_OPTIONS,
      width: container.clientWidth,
      height,
      rightPriceScale: {
        borderColor: COLORS.border,
        scaleMargins: { top: 0.08, bottom: 0.22 },
      },
    })
    mainChart.current = chart

    // Candles
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: COLORS.gain,
      downColor: COLORS.loss,
      borderUpColor: COLORS.gain,
      borderDownColor: COLORS.loss,
      wickUpColor: COLORS.gain,
      wickDownColor: COLORS.loss,
    })
    candleSeries.current = candles

    // Volume histogram (separate price scale)
    const volume = chart.addSeries(HistogramSeries, {
      priceScaleId: 'volume',
      color: COLORS.gainAlpha,
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })
    volumeSeries.current = volume

    const ohlcv = chartData.data
    const times = ohlcv.map((d) => toUnixTime(d.timestamp))
    const closes = ohlcv.map((d) => d.close)

    candles.setData(buildCandleData(ohlcv))
    volume.setData(buildVolumeData(ohlcv))

    // Bollinger Bands (if toggled on)
    if (showBB) {
      const { upper, middle, lower } = calcBollingerBands(closes)
      const bbUpper = chart.addSeries(LineSeries, { color: COLORS.brand, lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
      const bbMiddle = chart.addSeries(LineSeries, { color: `${COLORS.text}88`, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false })
      const bbLower = chart.addSeries(LineSeries, { color: COLORS.brand, lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
      bbUpper.setData(buildLineData(times, upper))
      bbMiddle.setData(buildLineData(times, middle))
      bbLower.setData(buildLineData(times, lower))
      bbUpperRef.current = bbUpper
      bbMiddleRef.current = bbMiddle
      bbLowerRef.current = bbLower
    }

    // Crosshair tooltip
    chart.subscribeCrosshairMove((param) => {
      if (!param || !param.time || !param.seriesData) {
        setTooltip(null)
        return
      }
      const candlePoint = param.seriesData.get(candles) as CandlestickData | undefined
      const volPoint = param.seriesData.get(volume) as HistogramData | undefined
      if (!candlePoint) { setTooltip(null); return }
      // Find matching OHLCV for volume
      const vol = volPoint?.value ?? 0
      setTooltip({
        time: new Date((param.time as number) * 1000).toLocaleString(),
        open: candlePoint.open,
        high: candlePoint.high,
        low: candlePoint.low,
        close: candlePoint.close,
        volume: vol,
      })
    })

    chart.timeScale().fitContent()

    // RSI pane
    if (showRSI && rsiRef.current) {
      const rsiContainer = rsiRef.current
      const rsiChart = createPaneChart(rsiContainer, 100)
      rsiChartRef.current = { chart: rsiChart, container: rsiContainer }

      const rsiValues = calcRSI(closes)
      const rsiSeries = rsiChart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1, priceLineVisible: false, lastValueVisible: true })
      rsiSeries.setData(buildLineData(times, rsiValues))

      // Overbought / oversold reference lines
      const ob = rsiChart.addSeries(LineSeries, { color: `${COLORS.loss}66`, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false })
      const os = rsiChart.addSeries(LineSeries, { color: `${COLORS.gain}66`, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false })
      ob.setData(times.map((t) => ({ time: t, value: 70 })))
      os.setData(times.map((t) => ({ time: t, value: 30 })))
      rsiChart.timeScale().fitContent()
    }

    // MACD pane
    if (showMACD && macdRef.current) {
      const macdContainer = macdRef.current
      const macdChart = createPaneChart(macdContainer, 100)
      macdChartRef.current = { chart: macdChart, container: macdContainer }

      const { macd, signal, histogram } = calcMACD(closes)
      const macdLineSeries = macdChart.addSeries(LineSeries, { color: COLORS.brand, lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
      const signalSeries = macdChart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
      const histSeries = macdChart.addSeries(HistogramSeries, { priceScaleId: 'right', lastValueVisible: false })

      macdLineSeries.setData(buildLineData(times, macd))
      signalSeries.setData(buildLineData(times, signal))
      histSeries.setData(buildHistogramData(times, histogram))
      macdChart.timeScale().fitContent()
    }

    // ResizeObserver
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      const w = entry.contentRect.width
      chart.applyOptions({ width: w })
      rsiChartRef.current?.chart.applyOptions({ width: w })
      macdChartRef.current?.chart.applyOptions({ width: w })
    })
    ro.observe(container)

    return () => {
      ro.disconnect()
      destroyCharts()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chartData, height, showBB, showRSI, showMACD])

  // ─ Cleanup on unmount ────────────────────────────────────────────────────

  useEffect(() => {
    return () => destroyCharts()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ─ Render ────────────────────────────────────────────────────────────────

  return (
    <div className={cn('flex flex-col gap-0 rounded-lg overflow-hidden bg-[#0a0e1a] border border-[#1f2d40]', className)}>
      {/* Controls row */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1f2d40]">
        {/* Time range selector */}
        <div className="flex items-center gap-1">
          {(['1D', '1W', '1M', '3M', '1Y'] as TimeRange[]).map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={cn(
                'px-3 py-1 rounded text-xs font-medium transition-colors',
                range === r
                  ? 'bg-[#6366f1] text-white'
                  : 'text-[#94a3b8] hover:text-white hover:bg-[#1a2235]',
              )}
            >
              {r}
            </button>
          ))}
        </div>

        {/* Overlay toggles */}
        <div className="flex items-center gap-1">
          {[
            { key: 'BB', active: showBB, toggle: () => setShowBB((v) => !v) },
            { key: 'RSI', active: showRSI, toggle: () => setShowRSI((v) => !v) },
            { key: 'MACD', active: showMACD, toggle: () => setShowMACD((v) => !v) },
          ].map(({ key, active, toggle }) => (
            <button
              key={key}
              onClick={toggle}
              className={cn(
                'px-3 py-1 rounded text-xs font-medium border transition-colors',
                active
                  ? 'bg-[#6366f1]/20 border-[#6366f1] text-[#6366f1]'
                  : 'border-[#1f2d40] text-[#94a3b8] hover:border-[#6366f1]/50 hover:text-white',
              )}
            >
              {key}
            </button>
          ))}
        </div>
      </div>

      {/* OHLCV tooltip */}
      {tooltip && (
        <div className="flex items-center gap-4 px-4 py-2 border-b border-[#1f2d40] text-xs font-mono bg-[#111827]">
          <span className="text-[#94a3b8]">{tooltip.time}</span>
          <span className="text-[#94a3b8]">O <span className="text-white">{formatCurrency(tooltip.open)}</span></span>
          <span className="text-[#94a3b8]">H <span className="text-[#00C851]">{formatCurrency(tooltip.high)}</span></span>
          <span className="text-[#94a3b8]">L <span className="text-[#FF4444]">{formatCurrency(tooltip.low)}</span></span>
          <span className="text-[#94a3b8]">C{' '}
            <span className={tooltip.close >= tooltip.open ? 'text-[#00C851]' : 'text-[#FF4444]'}>
              {formatCurrency(tooltip.close)}
            </span>
          </span>
          <span className="text-[#94a3b8]">V <span className="text-white">{formatCompact(tooltip.volume)}</span></span>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div
          style={{ height }}
          className="flex items-center justify-center bg-[#0a0e1a] animate-pulse"
        >
          <div className="w-full h-full bg-[#111827] rounded" />
        </div>
      )}

      {/* Error state */}
      {isError && !isLoading && (
        <div
          style={{ height }}
          className="flex items-center justify-center bg-[#0a0e1a] text-[#94a3b8] text-sm"
        >
          Unable to load chart data for <strong className="ml-1 text-white">{ticker}</strong>
        </div>
      )}

      {/* Main chart container */}
      {!isLoading && !isError && (
        <div ref={mainRef} style={{ height }} className="w-full" />
      )}

      {/* RSI pane */}
      {showRSI && !isLoading && !isError && (
        <div className="border-t border-[#1f2d40]">
          <div className="flex items-center gap-2 px-4 pt-2 pb-1">
            <span className="text-[10px] font-medium text-[#f59e0b] uppercase tracking-wider">RSI (14)</span>
            <span className="text-[10px] text-[#94a3b8]">70 overbought · 30 oversold</span>
          </div>
          <div ref={rsiRef} className="w-full" style={{ height: 100 }} />
        </div>
      )}

      {/* MACD pane */}
      {showMACD && !isLoading && !isError && (
        <div className="border-t border-[#1f2d40]">
          <div className="flex items-center gap-2 px-4 pt-2 pb-1">
            <span className="text-[10px] font-medium text-[#6366f1] uppercase tracking-wider">MACD (12,26,9)</span>
            <span className="text-[10px] text-[#f59e0b]">— Signal</span>
          </div>
          <div ref={macdRef} className="w-full" style={{ height: 100 }} />
        </div>
      )}
    </div>
  )
}
