"use client";

import { PetList } from "@/components/pets/pet-list";
import Link from "next/link";
import { Plus } from "lucide-react";

export default function PetsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">My Pets</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage your pet profiles and view their health history.
          </p>
        </div>
        <Link
          href="/pets/new"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground shadow-sm transition-all hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          Add Pet
        </Link>
      </div>
      <PetList />
    </div>
  );
}
