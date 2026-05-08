import Link from "next/link";
import { ArrowRight, Camera, ChartBar, Dog, Shield, Sparkles, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 w-full border-b border-border/60 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Dog className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-foreground">DietPaw</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/sign-in"
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              Sign in
            </Link>
            <Link
              href="/sign-up"
              className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-all hover:bg-primary/90"
            >
              Get started free
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden px-4 py-24 sm:py-32">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-transparent to-transparent" />
        <div className="container mx-auto max-w-4xl text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-sm text-primary">
            <Sparkles className="h-3.5 w-3.5" />
            AI-powered nutrition for your dog
          </div>
          <h1 className="mb-6 text-4xl font-bold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Know your dog's breed.
            <br />
            <span className="text-primary">Feed them right.</span>
          </h1>
          <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground">
            Upload a photo of any dog. Our AI identifies the breed in seconds and generates a
            personalized, science-backed diet plan based on NRC/AAFCO nutritional guidelines.
          </p>
          <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/sign-up"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-8 py-3.5 text-base font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:bg-primary/90 hover:shadow-xl sm:w-auto"
            >
              Start free — no credit card
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/sign-in"
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-background px-8 py-3.5 text-base font-medium text-foreground transition-all hover:bg-muted sm:w-auto"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border px-4 py-20">
        <div className="container mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <h2 className="mb-3 text-3xl font-bold text-foreground">Everything your dog needs</h2>
            <p className="text-muted-foreground">
              From photo to personalized diet plan in under 2 seconds.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {[
              {
                icon: Camera,
                title: "AI Breed Detection",
                description:
                  "EfficientNet-B4 model identifies from 120 dog breeds with confidence scoring. Works from photos or live camera.",
              },
              {
                icon: ChartBar,
                title: "Science-Based Nutrition",
                description:
                  "Diet plans calculated using NRC/AAFCO guidelines. Real caloric calculations, not keyword matching.",
              },
              {
                icon: Zap,
                title: "Instant Personalization",
                description:
                  "Breed overlays for 30+ conditions: obesity-prone, bloat risk, joint support, low-purine, and more.",
              },
              {
                icon: Dog,
                title: "Multi-Pet Profiles",
                description:
                  "Track multiple pets with complete health history, diet records, and AI prediction history.",
              },
              {
                icon: Shield,
                title: "Vet-Ready Reports",
                description:
                  "Download professional PDF reports with complete nutritional breakdown and feeding schedules.",
              },
              {
                icon: Sparkles,
                title: "Always Improving",
                description:
                  "Continuously fine-tuned model. Supplement recommendations for joint, heart, coat, and digestive health.",
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="group rounded-2xl border border-border bg-card p-6 transition-all hover:border-primary/30 hover:shadow-md"
              >
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                  <feature.icon className="h-5 w-5" />
                </div>
                <h3 className="mb-2 font-semibold text-foreground">{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border px-4 py-20">
        <div className="container mx-auto max-w-2xl text-center">
          <h2 className="mb-4 text-3xl font-bold text-foreground">
            Give your dog the nutrition they deserve
          </h2>
          <p className="mb-8 text-muted-foreground">
            Join thousands of pet owners using AI-powered nutrition planning. Free forever for 1 pet.
          </p>
          <Link
            href="/sign-up"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-8 py-3.5 text-base font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:bg-primary/90"
          >
            Get started free
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-border px-4 py-8">
        <div className="container mx-auto flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <div className="flex items-center gap-2">
            <Dog className="h-4 w-4" />
            <span>DietPaw © {new Date().getFullYear()}</span>
          </div>
          <p className="text-xs">
            AI recommendations are for informational purposes only. Consult your veterinarian.
          </p>
        </div>
      </footer>
    </div>
  );
}
