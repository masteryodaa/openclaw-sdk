"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listTemplates, createFromTemplate } from "@/lib/api";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Template } from "@/lib/types";

const CATEGORIES = ["all", "web", "backend", "data", "tools", "ai"];

const difficultyColor: Record<string, string> = {
  easy: "text-emerald-400 border-emerald-500/20 bg-emerald-500/10",
  medium: "text-amber-400 border-amber-500/20 bg-amber-500/10",
  hard: "text-red-400 border-red-500/20 bg-red-500/10",
};

export default function TemplatesPage() {
  const router = useRouter();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [category, setCategory] = useState("all");
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    listTemplates().then(setTemplates).catch(console.error);
  }, []);

  const filtered = category === "all"
    ? templates
    : templates.filter((t) => t.category === category);

  const handleUseTemplate = async (template: Template) => {
    setLoading(template.id);
    try {
      const project = await createFromTemplate(template.id);
      router.push(`/workspace/${project.id}`);
    } catch (err) {
      console.error("Failed:", err);
      setLoading(null);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold mb-2">Templates</h1>
      <p className="text-zinc-400 mb-6">
        Start with a pre-built template to jumpstart your project.
      </p>

      {/* Category filter */}
      <div className="flex gap-2 mb-6">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`rounded-full px-4 py-1.5 text-sm capitalize transition-colors ${
              category === cat
                ? "bg-emerald-600 text-white"
                : "border border-zinc-700 text-zinc-400 hover:text-white hover:border-zinc-500"
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Template grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((template) => (
          <Card key={template.id} className="border-zinc-800 bg-zinc-900 flex flex-col">
            <CardHeader>
              <div className="flex items-start justify-between">
                <CardTitle className="text-base">{template.name}</CardTitle>
                <Badge variant="outline" className={difficultyColor[template.difficulty] || ""}>
                  {template.difficulty}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="flex-1">
              <p className="text-sm text-zinc-400 mb-3">{template.description}</p>
              <div className="flex flex-wrap gap-1">
                {template.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-zinc-800 px-2 py-0.5 text-xs text-zinc-500"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </CardContent>
            <CardFooter>
              <Button
                onClick={() => handleUseTemplate(template)}
                disabled={loading === template.id}
                className="w-full bg-emerald-600 hover:bg-emerald-500"
                size="sm"
              >
                {loading === template.id ? "Creating..." : "Use Template"}
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  );
}
