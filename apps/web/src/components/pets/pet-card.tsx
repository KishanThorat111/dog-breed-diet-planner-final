"use client";

import type { Pet } from "@/types";
import Link from "next/link";
import { useDeletePet } from "@/hooks/use-pets";
import { formatAge, formatWeight } from "@/lib/utils";
import { Activity, Dog, MoreVertical, Trash2 } from "lucide-react";
import { useState } from "react";

interface PetCardProps {
  pet: Pet;
}

export function PetCard({ pet }: PetCardProps) {
  const { mutate: deletePet } = useDeletePet();
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div className="group relative rounded-2xl border border-border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Dog className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-foreground">{pet.name}</h3>
            <p className="text-sm text-muted-foreground">
              {pet.breed ? pet.breed.replace(/_/g, " ") : "Breed unknown"}
            </p>
          </div>
        </div>

        <div className="relative">
          <button
            onClick={() => setShowMenu((v) => !v)}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground opacity-0 transition-all hover:bg-muted group-hover:opacity-100"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
          {showMenu && (
            <div className="absolute right-0 top-9 z-10 min-w-32 rounded-xl border border-border bg-card py-1 shadow-lg">
              <button
                onClick={() => {
                  setShowMenu(false);
                  if (confirm(`Delete ${pet.name}?`)) deletePet(pet.id);
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <div>
          <p className="text-xs text-muted-foreground">Age</p>
          <p className="font-medium text-foreground">{formatAge(pet.age_months)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Weight</p>
          <p className="font-medium text-foreground">{formatWeight(pet.weight_kg)}</p>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <Activity className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs text-muted-foreground capitalize">
          {pet.activity_level} activity · {pet.life_stage}
        </span>
      </div>

      <Link
        href={`/pets/${pet.id}`}
        className="mt-4 flex w-full items-center justify-center rounded-lg border border-border py-2 text-sm font-medium text-muted-foreground transition-all hover:border-primary/40 hover:text-foreground"
      >
        View Details
      </Link>
    </div>
  );
}
