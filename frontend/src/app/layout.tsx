"use client";

import React from "react";
import {
  ConfigProvider,
  Layout,
  Menu,
  theme,
  Switch,
  Breadcrumb,
  Space,
} from "antd";
import {
  DashboardOutlined,
  FileTextOutlined,
  UploadOutlined,
  IdcardOutlined,
  SunOutlined,
  MoonOutlined,
  HomeOutlined,
} from "@ant-design/icons";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAppStore } from "@/stores";
import "./globals.css";

const { Header, Content, Sider } = Layout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/upload", icon: <UploadOutlined />, label: "上传简历" },
  { key: "/jobs", icon: <IdcardOutlined />, label: "岗位管理" },
  { key: "/reports", icon: <FileTextOutlined />, label: "匹配报告" },
];

// Auto-generate breadcrumbs from pathname
function getBreadcrumbs(pathname: string) {
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) {
    return [{ label: "仪表盘", href: "/" }];
  }

  const items: { label: string; href?: string }[] = [];
  let accumulated = "";
  for (const seg of segments) {
    accumulated += `/${seg}`;
    // Special case: match detail page
    if (seg === "match" && segments.length > 1) continue;
    if (accumulated === "/match") continue;

    const labels: Record<string, string> = {
      upload: "上传简历",
      jobs: "岗位管理",
      reports: "匹配报告",
      match: "匹配详情",
    };
    items.push({
      label: labels[seg] || seg,
      href: accumulated,
    });
  }

  // For /match/[id], add "匹配详情"
  if (segments[0] === "match") {
    items.push({ label: "匹配详情" });
  }

  return items;
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { token } = theme.useToken();
  const appTheme = useAppStore((s) => s.theme);
  const toggleTheme = useAppStore((s) => s.toggleTheme);

  const isDark = appTheme === "dark";
  const breadcrumbs = getBreadcrumbs(pathname);

  return (
    <html lang="zh-CN">
      <body>
        <ConfigProvider
          theme={{
            algorithm: isDark
              ? theme.darkAlgorithm
              : theme.defaultAlgorithm,
            token: {
              colorPrimary: "#1677ff",
              borderRadius: 6,
            },
          }}
        >
          <Layout style={{ minHeight: "100vh" }}>
            <Sider
              breakpoint="lg"
              collapsedWidth="80"
              style={{ background: isDark ? "#141414" : "#fff" }}
            >
              <Link href="/" style={{ textDecoration: "none" }}>
                <div
                  style={{
                    height: 64,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    fontSize: 18,
                    color: token.colorPrimary,
                    borderBottom: `1px solid ${token.colorBorderSecondary}`,
                  }}
                >
                  📋 简历匹配
                </div>
              </Link>
              <Menu
                mode="inline"
                selectedKeys={[pathname === "/" ? "/" : `/${pathname.split("/")[1]}`]}
                items={menuItems}
                onClick={({ key }) => router.push(key)}
                style={{ borderRight: 0, marginTop: 8 }}
              />
            </Sider>
            <Layout>
              <Header
                style={{
                  background: isDark ? "#141414" : "#fff",
                  padding: "0 24px",
                  borderBottom: `1px solid ${token.colorBorderSecondary}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <span
                    style={{
                      fontSize: 16,
                      fontWeight: 500,
                      color: token.colorTextHeading,
                    }}
                  >
                    AI 简历智能解析与岗位匹配系统
                  </span>
                </div>
                <Space>
                  <Switch
                    checked={isDark}
                    onChange={toggleTheme}
                    checkedChildren={<MoonOutlined />}
                    unCheckedChildren={<SunOutlined />}
                  />
                </Space>
              </Header>

              {/* Breadcrumb area */}
              <div
                style={{
                  padding: "12px 24px 0",
                  background: isDark ? "#141414" : "#fff",
                }}
              >
                <Breadcrumb
                  items={[
                    {
                      title: (
                        <Link href="/">
                          <HomeOutlined style={{ marginRight: 4 }} />
                          首页
                        </Link>
                      ),
                    },
                    ...breadcrumbs.map((b) => ({
                      title: b.href ? (
                        <Link href={b.href}>{b.label}</Link>
                      ) : (
                        b.label
                      ),
                    })),
                  ]}
                />
              </div>

              <Content
                style={{
                  margin: 24,
                  padding: 24,
                  background: isDark ? "#141414" : "#fff",
                  borderRadius: 8,
                  minHeight: 280,
                }}
              >
                {children}
              </Content>
            </Layout>
          </Layout>
        </ConfigProvider>
      </body>
    </html>
  );
}
