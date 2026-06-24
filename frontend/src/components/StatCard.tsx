"use client";

import { Card, Skeleton, Typography } from "antd";
import type { ReactNode } from "react";

const { Text } = Typography;

interface StatCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  suffix?: string;
  loading?: boolean;
  color?: string;
}

export default function StatCard({
  title,
  value,
  icon,
  suffix,
  loading = false,
  color = "#1677ff",
}: StatCardProps) {
  return (
    <Card
      hoverable
      style={{ height: "100%" }}
      styles={{ body: { padding: "20px 24px" } }}
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 1 }} />
      ) : (
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <Text type="secondary" style={{ fontSize: 14 }}>
              {title}
            </Text>
            <div className="mt-2 flex items-baseline gap-1">
              <span
                style={{ fontSize: 32, fontWeight: 700, color, lineHeight: 1 }}
              >
                {value}
              </span>
              {suffix && (
                <Text type="secondary" style={{ fontSize: 14 }}>
                  {suffix}
                </Text>
              )}
            </div>
          </div>
          {icon && (
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 12,
                background: `${color}15`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 28,
                color,
              }}
            >
              {icon}
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
