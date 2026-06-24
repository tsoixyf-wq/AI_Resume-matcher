"use client";

import { Tag } from "antd";

interface ScoreTagProps {
  score: number;
  showValue?: boolean;
}

const getScoreColor = (score: number): string => {
  if (score >= 8) return "#52c41a";
  if (score >= 6) return "#1677ff";
  if (score >= 4) return "#faad14";
  return "#f5222d";
};

const getScoreLabel = (score: number): string => {
  if (score >= 9) return "极佳";
  if (score >= 8) return "优秀";
  if (score >= 6) return "良好";
  if (score >= 4) return "一般";
  return "较低";
};

export default function ScoreTag({ score, showValue = true }: ScoreTagProps) {
  const color = getScoreColor(score);
  return (
    <Tag color={color} style={{ fontWeight: 600 }}>
      {showValue ? `${score.toFixed(1)} 分` : getScoreLabel(score)}{" "}
      {getScoreLabel(score)}
    </Tag>
  );
}

export { getScoreColor, getScoreLabel };
