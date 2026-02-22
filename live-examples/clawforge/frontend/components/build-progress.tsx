interface BuildEvent {
  event: string;
  detail: string;
}

const STEPS = ["plan", "build", "review"];

export function BuildProgress({ events }: { events: BuildEvent[] }) {
  const completedSteps = events
    .filter((e) => e.event === "step_complete")
    .map((e) => e.detail.split(" ")[0]);

  const currentStep = events
    .filter((e) => e.event === "step_start")
    .map((e) => e.detail.split(" ")[0])
    .pop();

  const hasError = events.some((e) => e.event.includes("error") || e.event.includes("Error"));
  const isComplete = events.some((e) => e.event === "build_complete");

  return (
    <div className="py-4 space-y-6">
      {/* Step progress */}
      <div className="flex items-center gap-2">
        {STEPS.map((step, i) => {
          const done = completedSteps.includes(step);
          const active = currentStep === step;

          return (
            <div key={step} className="flex items-center gap-2">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold ${
                  done
                    ? "bg-emerald-500 text-white"
                    : active
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500"
                    : "bg-zinc-800 text-zinc-500 border border-zinc-700"
                }`}
              >
                {done ? "\u2713" : i + 1}
              </div>
              <span
                className={`text-sm capitalize ${
                  done ? "text-emerald-400" : active ? "text-white" : "text-zinc-500"
                }`}
              >
                {step}
              </span>
              {i < STEPS.length - 1 && (
                <div
                  className={`h-px w-8 ${done ? "bg-emerald-500" : "bg-zinc-700"}`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Status */}
      {isComplete && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-emerald-400">
          Build complete!
        </div>
      )}
      {hasError && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400">
          Build encountered an error.
        </div>
      )}

      {/* Event log */}
      {events.length > 0 && (
        <div className="space-y-1">
          <h3 className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Build Log</h3>
          {events.map((ev, i) => (
            <div key={i} className="text-xs font-mono text-zinc-500">
              [{ev.event}] {ev.detail}
            </div>
          ))}
        </div>
      )}

      {events.length === 0 && (
        <p className="text-zinc-500 text-sm text-center py-8">
          Click &quot;Build&quot; to start a multi-agent build pipeline.
        </p>
      )}
    </div>
  );
}
