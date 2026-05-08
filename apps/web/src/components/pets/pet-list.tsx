"use client";

import { usePets } from "@/hooks/use-pets";
import { PetCard } from "./pet-card";
import { Loader2 } from "lucide-react";
import Link from "next/link";

export function PetList() {
  const { pets, isLoading } = usePets();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!pets || pets.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-muted/20 py-16 text-center">
        <p className="text-muted-foreground">No pets added yet.</p>
        <Link
          href="/pets/new"
          className="mt-3 inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Add your first pet
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {pets.map((pet) => (
        <PetCard key={pet.id} pet={pet} />
      ))}
    </div>
  );
}
