import Link from "next/link";
import { ArrowRight, Camera, Dog, FileText, Plus, Sparkles } from "lucide-react";

export const metadata = { title: "Dashboard" };

export default function DashboardPage() {
  const firstName = "there";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground sm:text-3xl">
          Good morning, {firstName} 👋
        </h1>
        <p className="mt-1 text-muted-foreground">
          Here's what's happening with your pets today.
        </p>
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Quick Actions
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Link
            href="/analyze"
            className="group flex items-start gap-4 rounded-2xl border border-border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-md"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
              <Camera className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Analyze a Dog</h3>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Upload or capture a photo for AI breed identification
              </p>
            </div>
            <ArrowRight className="ml-auto h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1" />
          </Link>

          <Link
            href="/pets/new"
            className="group flex items-start gap-4 rounded-2xl border border-border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-md"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 transition-colors group-hover:bg-emerald-500 group-hover:text-white dark:text-emerald-400">
              <Plus className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Add a Pet</h3>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Create a pet profile to track health and diet history
              </p>
            </div>
            <ArrowRight className="ml-auto h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1" />
          </Link>

          <Link
            href="/reports"
            className="group flex items-start gap-4 rounded-2xl border border-border bg-card p-5 transition-all hover:border-primary/40 hover:shadow-md"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-500/10 text-amber-600 transition-colors group-hover:bg-amber-500 group-hover:text-white dark:text-amber-400">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-semibold text-foreground">Download Reports</h3>
              <p className="mt-0.5 text-sm text-muted-foreground">
                Export professional PDF diet reports for your vet
              </p>
            </div>
            <ArrowRight className="ml-auto h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-1" />
          </Link>
        </div>
      </div>

      {/* Stats placeholder — connected to real data via client components */}
      <div>
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Your Activity
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { label: "Pets", value: "—", icon: Dog, color: "text-primary" },
            { label: "Analyses", value: "—", icon: Sparkles, color: "text-emerald-500" },
            { label: "Diet Plans", value: "—", icon: FileText, color: "text-amber-500" },
            { label: "Reports", value: "—", icon: Camera, color: "text-rose-500" },
          ].map((stat) => (
            <div
              key={stat.label}
              className="rounded-2xl border border-border bg-card p-5"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">{stat.label}</span>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
              <p className="mt-2 text-2xl font-bold text-foreground">{stat.value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
