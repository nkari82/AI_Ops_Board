import React from "react";
import type { BoardCategory, Domain } from "@/types";
import { domains, categories } from "@/lib/constants";
import { Pill } from "@/components/shared/Pill";
import { DomainIcon } from "@/components/shared/DomainIcon";
import { Search } from "lucide-react";

interface BoardFiltersProps {
  query: string;
  selectedCategory: BoardCategory | "전체";
  selectedDomain: Domain | "전체";
  onQueryChange: (value: string) => void;
  onCategoryChange: (value: BoardCategory | "전체") => void;
  onDomainChange: (value: Domain | "전체") => void;
}

export function BoardFilters({
  query,
  selectedCategory,
  selectedDomain,
  onQueryChange,
  onCategoryChange,
  onDomainChange,
}: BoardFiltersProps) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="relative min-w-0 flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="Claude Code, AGENTS.md, Unity GC, MCP 검색"
            className="h-11 w-full rounded-2xl border border-slate-200 bg-slate-50 pl-10 pr-4 text-sm outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Pill active={selectedCategory === "전체"} onClick={() => onCategoryChange("전체")}>
            전체
          </Pill>
          {categories.map((category) => (
            <Pill
              key={category}
              active={selectedCategory === category}
              onClick={() => onCategoryChange(category)}
            >
              {category}
            </Pill>
          ))}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
        <Pill active={selectedDomain === "전체"} onClick={() => onDomainChange("전체")}>
          전체 분야
        </Pill>
        {domains.map((domain) => (
          <Pill key={domain} active={selectedDomain === domain} onClick={() => onDomainChange(domain)}>
            <span className="inline-flex items-center gap-1">
              <DomainIcon domain={domain} /> {domain}
            </span>
          </Pill>
        ))}
      </div>
    </section>
  );
}
