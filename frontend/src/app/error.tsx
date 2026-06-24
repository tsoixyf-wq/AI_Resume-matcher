"use client";

import { Button, Result } from "antd";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <Result
      status="error"
      title="页面出错了"
      subTitle={error?.message || "发生了未知错误，请稍后重试"}
      extra={
        <Button type="primary" onClick={reset}>
          重新加载
        </Button>
      }
    />
  );
}
