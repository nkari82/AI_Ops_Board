import React from "react";
import { Card, CardContent } from "@/components/ui/card";

interface MetricProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  caption: string;
}

export function Metric({ icon, label, value, caption }: MetricProps) {
  return (
    <Card className="rounded-3xl border-slate-200 bg-white shadow-sm">
      <CardContent className="p-5">
        <div className="rounded-2xl bg-slate-100 p-2 text-slate-700 w-fit">{icon}</div>
        <div className="mt-4 text-sm font-medium text-slate-500">{label}</div>
        <div className="mt-1 text-2xl font-bold">{value}</div>
        <div className="mt-1 text-xs text-slate-500">{caption}</div>
      </CardContent>
    </Card>
  );
}
