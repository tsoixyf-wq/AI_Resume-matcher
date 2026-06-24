"use client";

import { useState } from "react";
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Tag,
  message,
  Space,
  Descriptions,
  Switch,
} from "antd";
import { PlusOutlined, EyeOutlined } from "@ant-design/icons";
import { createJob, listJobs, getJob, deleteJob, toggleJobActive } from "@/lib/api";
import type { JDItem } from "@/lib/types";
import { PageHeader, ConfirmButton, EmptyState, ErrorState } from "@/components";
import useApi from "@/hooks/useApi";

const { TextArea } = Input;

export default function JobsPage() {
  const {
    data: jobs,
    loading,
    error,
    refresh,
  } = useApi<JDItem[]>(() => listJobs({ page_size: 50 }).then((d) => d.items));

  const [createOpen, setCreateOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<JDItem | null>(null);
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);

  if (error && !loading) {
    return <ErrorState message={error} onRetry={refresh} />;
  }

  async function handleCreate(values: {
    title: string;
    department?: string;
    location?: string;
    raw_text: string;
  }) {
    setSubmitting(true);
    try {
      await createJob(values);
      message.success("岗位创建成功，正在 AI 解析...");
      setCreateOpen(false);
      form.resetFields();
      refresh();
    } catch (e: any) {
      message.error(`创建失败: ${e?.response?.data?.detail || e.message}`);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleView(id: string) {
    try {
      const data = await getJob(id);
      setDetail(data);
      setDetailOpen(true);
    } catch {
      message.error("获取详情失败");
    }
  }

  async function handleDelete(id: string) {
    await deleteJob(id);
    message.success("删除成功");
    refresh();
  }

  async function handleToggleActive(id: string) {
    try {
      const result = await toggleJobActive(id);
      message.success(result.is_active ? "已启用" : "已停用");
      refresh();
    } catch {
      message.error("操作失败");
    }
  }

  const importanceColor: Record<string, string> = {
    required: "red",
    preferred: "blue",
    "nice-to-have": "default",
  };

  const columns = [
    {
      title: "岗位名称",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
    },
    {
      title: "部门",
      dataIndex: "department",
      key: "dept",
      width: 120,
      render: (d: string | null) => d || "-",
    },
    {
      title: "地点",
      dataIndex: "location",
      key: "loc",
      width: 100,
      render: (l: string | null) => l || "-",
    },
    {
      title: "状态",
      dataIndex: "parse_status",
      key: "status",
      width: 90,
      render: (s: string) => (
        <Tag color={s === "completed" ? "green" : "blue"}>
          {s === "completed" ? "已解析" : s}
        </Tag>
      ),
    },
    {
      title: "启用",
      dataIndex: "is_active",
      key: "active",
      width: 70,
      render: (v: boolean, record: JDItem) => (
        <Switch
          size="small"
          checked={v}
          onChange={() => handleToggleActive(record.id)}
        />
      ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "date",
      width: 110,
      render: (d: string) => d?.slice(0, 10),
    },
    {
      title: "操作",
      key: "actions",
      width: 160,
      render: (_: unknown, record: JDItem) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleView(record.id)}
          >
            查看
          </Button>
          <ConfirmButton
            type="link"
            title="确认删除"
            content="确定要删除这个岗位吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            删除
          </ConfirmButton>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="岗位管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateOpen(true)}
          >
            新建岗位
          </Button>
        }
      />

      <Card>
        <Table
          dataSource={jobs || []}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 个岗位` }}
          locale={{
            emptyText: (
              <EmptyState
                title="暂无岗位"
                description="创建第一个岗位开始匹配"
                actionLabel="新建岗位"
                onAction={() => setCreateOpen(true)}
              />
            ),
          }}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="新建岗位"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()}
        confirmLoading={submitting}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="title"
            label="岗位名称"
            rules={[{ required: true, message: "请输入岗位名称" }]}
          >
            <Input placeholder="例如: AI 研发工程师" />
          </Form.Item>
          <Form.Item name="department" label="部门">
            <Input placeholder="例如: AI 平台部" />
          </Form.Item>
          <Form.Item name="location" label="工作地点">
            <Input placeholder="例如: 北京" />
          </Form.Item>
          <Form.Item
            name="raw_text"
            label="岗位描述 (JD)"
            rules={[{ required: true, message: "请粘贴岗位描述" }]}
          >
            <TextArea rows={12} placeholder="粘贴完整的岗位描述..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="岗位详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        width={800}
        footer={null}
      >
        {detail && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="岗位">{detail.title}</Descriptions.Item>
            <Descriptions.Item label="部门">
              {detail.department || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="地点">
              {detail.location || "-"}
            </Descriptions.Item>
            <Descriptions.Item label="技能要求">
              {detail.parsed_data.skills_required.length > 0
                ? detail.parsed_data.skills_required.map((s, i) => (
                    <Tag
                      key={i}
                      color={importanceColor[s.importance] || "default"}
                    >
                      {s.name}
                      {s.level ? ` (${s.level})` : ""}
                      {s.importance === "required" ? " [必备]" : ""}
                    </Tag>
                  ))
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="学历要求">
              {detail.parsed_data.education_required.min_degree || "不限"}
              {detail.parsed_data.education_required.preferred_majors.length >
                0 &&
                ` | 优先专业: ${detail.parsed_data.education_required.preferred_majors.join("、")}`}
            </Descriptions.Item>
            <Descriptions.Item label="经验要求">
              {detail.parsed_data.experience_required.min_years
                ? `${detail.parsed_data.experience_required.min_years} 年以上`
                : "不限"}
            </Descriptions.Item>
            <Descriptions.Item label="岗位职责">
              {detail.parsed_data.responsibilities.length > 0
                ? detail.parsed_data.responsibilities.map((r, i) => (
                    <div key={i}>• {r}</div>
                  ))
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="原始描述">
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  maxHeight: 300,
                  overflow: "auto",
                }}
              >
                {detail.raw_text}
              </pre>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
}
