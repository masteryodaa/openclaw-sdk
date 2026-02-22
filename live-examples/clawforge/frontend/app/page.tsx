"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { PromptInput } from "@/components/prompt-input";
import { createProject, createFromTemplate } from "@/lib/api";

const QUICK_STARTS = [
  { label: "Landing Page", template: "landing-page" },
  { label: "REST API", template: "rest-api" },
  { label: "Dashboard", template: "data-dashboard" },
  { label: "CLI Tool", template: "cli-tool" },
  { label: "Chatbot", template: "chatbot" },
];

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (description: string) => {
    setLoading(true);
    try {
      const project = await createProject(description);
      router.push(`/workspace/${project.id}`);
    } catch (err) {
      console.error("Failed to create project:", err);
      setLoading(false);
    }
  };

  const handleQuickStart = async (template: string) => {
    setLoading(true);
    try {
      const project = await createFromTemplate(template);
      router.push(`/workspace/${project.id}`);
    } catch (err) {
      console.error("Failed to create from template:", err);
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-3.5rem)] flex-col items-center justify-center px-4">
      <div className="w-full max-w-2xl space-y-8 -mt-20">
        <div className="text-center space-y-3">
          <h1 className="text-4xl font-bold tracking-tight">
            What do you want to{" "}
            <span className="text-emerald-500">build</span>?
          </h1>
          <p className="text-zinc-400 text-lg">
            Describe your idea and let AI agents bring it to life.
          </p>
        </div>

        <PromptInput onSubmit={handleSubmit} loading={loading} />

        <div className="flex flex-wrap justify-center gap-2">
          {QUICK_STARTS.map((qs) => (
            <button
              key={qs.template}
              onClick={() => handleQuickStart(qs.template)}
              disabled={loading}
              className="rounded-full border border-zinc-700 px-4 py-1.5 text-sm text-zinc-400 transition-colors hover:border-emerald-500/50 hover:text-emerald-400 disabled:opacity-50"
            >
              {qs.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
