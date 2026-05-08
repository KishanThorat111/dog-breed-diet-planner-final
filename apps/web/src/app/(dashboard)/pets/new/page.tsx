"use client";

import { PetForm } from "@/components/pets/pet-form";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function NewPetPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <Link
          href="/pets"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to pets
        </Link>
        <h1 className="mt-3 text-2xl font-bold text-foreground">Add a New Pet</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Enter your dog's details to create their profile and generate personalized diet plans.
        </p>
      </div>
      <PetForm />
    </div>
  );
}
