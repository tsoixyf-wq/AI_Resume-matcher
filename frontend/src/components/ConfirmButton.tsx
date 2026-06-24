"use client";

import { Button, Modal } from "antd";
import type { ButtonProps } from "antd";
import {
  DeleteOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";

interface ConfirmButtonProps extends Omit<ButtonProps, "onClick"> {
  title?: string;
  content?: string;
  onConfirm: () => void | Promise<void>;
  confirmLoading?: boolean;
}

export default function ConfirmButton({
  title = "确认操作",
  content = "确定要执行此操作吗？此操作不可撤销。",
  onConfirm,
  confirmLoading = false,
  children = "删除",
  danger = true,
  icon = <DeleteOutlined />,
  ...buttonProps
}: ConfirmButtonProps) {
  const handleClick = () => {
    Modal.confirm({
      title,
      icon: <ExclamationCircleOutlined />,
      content,
      okText: "确定",
      cancelText: "取消",
      okButtonProps: { danger, loading: confirmLoading },
      onOk: async () => {
        await onConfirm();
      },
    });
  };

  return (
    <Button
      danger={danger}
      icon={icon}
      onClick={handleClick}
      {...buttonProps}
    >
      {children}
    </Button>
  );
}
