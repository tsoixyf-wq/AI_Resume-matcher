"use client";

import { Button, Empty, Typography } from "antd";
import type { ReactNode } from "react";

const { Text } = Typography;

interface EmptyStateProps {
  icon?: ReactNode;
  title?: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function EmptyState({
  icon,
  title = "暂无数据",
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "60px 24px",
      }}
    >
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <div>
            <Text strong style={{ fontSize: 16 }}>
              {title}
            </Text>
            {description && (
              <div style={{ marginTop: 8 }}>
                <Text type="secondary">{description}</Text>
              </div>
            )}
          </div>
        }
      >
        {actionLabel && onAction && (
          <Button type="primary" onClick={onAction}>
            {actionLabel}
          </Button>
        )}
      </Empty>
      {icon && (
        <div style={{ fontSize: 64, marginBottom: 16, opacity: 0.3 }}>
          {icon}
        </div>
      )}
    </div>
  );
}
