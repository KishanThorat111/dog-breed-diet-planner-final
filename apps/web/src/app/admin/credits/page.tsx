"use client";

import React, { useState } from "react";
import { useApiClient } from "@/lib/api-client";

export default function CreditsAdmin() {
  const api = useApiClient();
  const [userId, setUserId] = useState("");
  const [credits, setCredits] = useState(0);
  const [result, setResult] = useState<any>(null);
  const user = tokenStorage.getUser();

  if (!user || !(user as any).is_admin) {
    return <div>Access denied: admin only.</div>;
  }

  const handleTopup = async () => {
    try {
      const res = await api.post("/admin/credits/topup", { user_id: userId, credits });
      setResult(res.data);
      alert("Topup successful: " + JSON.stringify(res.data));
    } catch (e: any) {
      alert("Topup failed: " + (e?.message || e));
    }
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Admin: Credits Topup</h2>
      <div className="space-y-2">
        <input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="User ID" className="border p-2 w-full" />
        <input type="number" value={credits} onChange={(e) => setCredits(parseInt(e.target.value || "0"))} className="border p-2 w-full" />
        <button onClick={handleTopup} className="bg-primary px-4 py-2 text-white rounded">Topup</button>
      </div>
      {result && <pre className="mt-4">{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}
