import React from "react";
import type { Domain } from "@/types";
import {
  Bot,
  Code2,
  Cpu,
  Database,
  Gamepad2,
  Network,
  Server,
  TerminalSquare,
} from "lucide-react";

export function DomainIcon({ domain }: { domain: Domain }) {
  switch (domain) {
    case "게임 클라이언트":
      return <Gamepad2 className="h-4 w-4" />;
    case "게임 서버":
      return <Server className="h-4 w-4" />;
    case "프론트엔드":
      return <Code2 className="h-4 w-4" />;
    case "백엔드":
      return <Database className="h-4 w-4" />;
    case "Unity":
      return <Cpu className="h-4 w-4" />;
    case "Unreal":
      return <TerminalSquare className="h-4 w-4" />;
    case "로컬 LLM":
      return <Bot className="h-4 w-4" />;
    case "Agent/MCP":
      return <Network className="h-4 w-4" />;
  }
}
