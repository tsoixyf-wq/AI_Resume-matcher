"use client";

import { Skeleton, Card } from "antd";

export default function Loading() {
  return (
    <div>
      <Skeleton active paragraph={{ rows: 1 }} style={{ marginBottom: 24 }} />
      <Card>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    </div>
  );
}
