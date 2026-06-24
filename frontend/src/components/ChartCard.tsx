"use client";

import { Card, Spin } from "antd";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { BarChart, PieChart, RadarChart } from "echarts/charts";
import {
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

// Register ALL chart types once — never again in individual pages
echarts.use([
  BarChart,
  PieChart,
  RadarChart,
  GridComponent,
  RadarComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  CanvasRenderer,
]);

interface ChartCardProps {
  title?: string;
  option: object;
  height?: number;
  loading?: boolean;
  className?: string;
}

export default function ChartCard({
  title,
  option,
  height = 300,
  loading = false,
  className,
}: ChartCardProps) {
  const chartRef = useRef<ReactEChartsCore>(null);

  useEffect(() => {
    // Resize chart when container changes
    const handleResize = () => chartRef.current?.getEchartsInstance()?.resize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  return (
    <Card title={title} className={className}>
      <Spin spinning={loading}>
        <ReactEChartsCore
          ref={chartRef}
          echarts={echarts}
          option={option}
          style={{ height }}
          notMerge
          lazyUpdate
        />
      </Spin>
    </Card>
  );
}

export { echarts };
