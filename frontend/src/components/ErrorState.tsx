"use client";

import { Button, Result } from "antd";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  message = "加载失败，请稍后重试",
  onRetry,
}: ErrorStateProps) {
  return (
    <Result
      status="error"
      title="加载出错"
      subTitle={message}
      extra={
        onRetry && (
          <Button type="primary" onClick={onRetry}>
            重新加载
          </Button>
        )
      }
    />
  );
}
