"use client";

import { Breadcrumb, Typography } from "antd";
import { HomeOutlined } from "@ant-design/icons";
import Link from "next/link";

const { Title } = Typography;

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  breadcrumbs?: BreadcrumbItem[];
  extra?: React.ReactNode;
}

export default function PageHeader({
  title,
  breadcrumbs,
  extra,
}: PageHeaderProps) {
  const items = [
    {
      title: (
        <Link href="/">
          <HomeOutlined /> 首页
        </Link>
      ),
    },
    ...(breadcrumbs || []).map((b) => ({
      title: b.href ? <Link href={b.href}>{b.label}</Link> : b.label,
    })),
  ];

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: 24,
      }}
    >
      <div>
        <Breadcrumb items={items} style={{ marginBottom: 8 }} />
        <Title level={4} style={{ margin: 0 }}>
          {title}
        </Title>
      </div>
      {extra && <div>{extra}</div>}
    </div>
  );
}
