"use client";

import { Card, Col, Row, Table, Button, Space } from "antd";
import {
  FileTextOutlined,
  IdcardOutlined,
  TrophyOutlined,
  RiseOutlined,
  UploadOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import Link from "next/link";
import {
  StatCard,
  ChartCard,
  ScoreTag,
  ErrorState,
  PageHeader,
} from "@/components";
import useApi from "@/hooks/useApi";
import { getDashboard } from "@/lib/api";
import type { DashboardData } from "@/lib/types";

export default function DashboardPage() {
  const { data, loading, error, refresh } =
    useApi<DashboardData>(getDashboard);

  if (error) {
    return <ErrorState message={error} onRetry={refresh} />;
  }

  const scoreDistOption = {
    tooltip: { trigger: "axis" as const },
    xAxis: {
      type: "category" as const,
      data: ["0-3分", "4-5分", "6-7分", "8-10分"],
      axisLabel: { color: "#8c8c8c" },
    },
    yAxis: { type: "value" as const, show: false },
    series: [
      {
        type: "bar",
        data: [
          data?.score_distribution?.["0-3"] || 0,
          data?.score_distribution?.["4-5"] || 0,
          data?.score_distribution?.["6-7"] || 0,
          data?.score_distribution?.["8-10"] || 0,
        ],
        itemStyle: {
          color: "#1677ff",
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
    grid: { top: 10, bottom: 20, left: 0, right: 0 },
  };

  const parseStatusOption = {
    tooltip: { trigger: "item" as const },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["50%", "50%"],
        data: [
          { value: data?.parse_status?.completed || 0, name: "已完成", itemStyle: { color: "#52c41a" } },
          { value: data?.parse_status?.processing || 0, name: "处理中", itemStyle: { color: "#1677ff" } },
          { value: data?.parse_status?.failed || 0, name: "失败", itemStyle: { color: "#f5222d" } },
          { value: data?.parse_status?.pending || 0, name: "待处理", itemStyle: { color: "#d9d9d9" } },
        ].filter((d) => d.value > 0),
        label: { show: false },
        emphasis: { label: { show: true, fontSize: 14, fontWeight: "bold" } },
      },
    ],
  };

  const topColumns = [
    {
      title: "简历",
      dataIndex: "resume_name",
      key: "resume",
      ellipsis: true,
    },
    {
      title: "匹配岗位",
      dataIndex: "job_title",
      key: "job",
      ellipsis: true,
    },
    {
      title: "匹配度",
      dataIndex: "score",
      key: "score",
      width: 120,
      render: (s: number) => <ScoreTag score={s} />,
      sorter: (a: any, b: any) => a.score - b.score,
    },
    {
      title: "日期",
      dataIndex: "date",
      key: "date",
      width: 120,
      render: (d: string) => d?.slice(0, 10),
    },
  ];

  return (
    <div>
      <PageHeader
        title="仪表盘"
        extra={
          <Space>
            <Link href="/upload">
              <Button type="primary" icon={<UploadOutlined />}>
                上传简历
              </Button>
            </Link>
            <Link href="/reports">
              <Button icon={<SearchOutlined />}>新建匹配</Button>
            </Link>
          </Space>
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="简历总数"
            value={data?.total_resumes ?? "-"}
            icon={<FileTextOutlined />}
            suffix="份"
            color="#1677ff"
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="岗位数量"
            value={data?.total_jobs ?? "-"}
            icon={<IdcardOutlined />}
            suffix="个"
            color="#52c41a"
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="匹配次数"
            value={data?.total_matches ?? "-"}
            icon={<TrophyOutlined />}
            suffix="次"
            color="#faad14"
            loading={loading}
          />
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <StatCard
            title="平均匹配分"
            value={data?.avg_score?.toFixed(1) ?? "-"}
            icon={<RiseOutlined />}
            suffix="/ 10"
            color="#722ed1"
            loading={loading}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <ChartCard
            title="匹配分数分布"
            option={scoreDistOption}
            height={260}
            loading={loading}
          />
        </Col>
        <Col xs={24} lg={12}>
          <ChartCard
            title="简历解析状态"
            option={parseStatusOption}
            height={260}
            loading={loading}
          />
        </Col>
      </Row>

      <Card title="最近匹配 Top 5">
        <Table
          columns={topColumns}
          dataSource={data?.top_matches || []}
          rowKey="match_id"
          loading={loading}
          pagination={false}
          size="middle"
          locale={{ emptyText: "暂无匹配记录" }}
        />
      </Card>
    </div>
  );
}
