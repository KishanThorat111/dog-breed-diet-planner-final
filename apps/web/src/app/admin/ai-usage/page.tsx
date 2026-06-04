"use client";

import React, { useEffect, useState } from "react";
import { useApiClient } from "@/lib/api-client";

export default function AIUsagePage() {
  const api = useApiClient();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await api.get("/admin/ai/usage?page=1&page_size=100");
        if (mounted) setItems(res.data.items || []);
      } catch (e) {
        console.error(e);
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [api]);

  if (loading) return <div>Loading AI usage...</div>;

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">AI Usage</h2>
      <table className="w-full table-auto">
        <thead>
          <tr>
            <th>User</th>
            <th>Provider</th>
            <th>Model</th>
            <th>Prompt</th>
            <th>Completion</th>
            <th>Caller</th>
            <th>At</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} className="border-t">
              <td>{it.user_id}</td>
              <td>{it.provider}</td>
              <td>{it.model}</td>
              <td>{it.prompt_tokens}</td>
              <td>{it.completion_tokens}</td>
              <td>{it.caller}</td>
              <td>{it.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
