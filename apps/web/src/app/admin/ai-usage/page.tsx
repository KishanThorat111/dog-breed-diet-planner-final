"use client";

import React, { useEffect, useState } from "react";
import { useApiClient } from "@/lib/api-client";

export default function AIUsagePage() {
  const api = useApiClient();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [total, setTotal] = useState(0);

  const fetchPage = async (p = 1) => {
    setLoading(true);
    try {
      const res = await api.get(`/admin/ai/usage?page=${p}&page_size=${pageSize}`);
      setItems(res.data.items || []);
      setTotal(res.data.total || 0);
      setPage(res.data.page || p);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPage(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <div>Loading AI usage...</div>;

  const pages = Math.ceil(total / pageSize) || 0;

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

      <div className="mt-4 flex items-center gap-2">
        <button
          onClick={() => fetchPage(Math.max(1, page - 1))}
          disabled={page <= 1}
          className="px-3 py-1 rounded border"
        >
          Prev
        </button>
        <span>
          Page {page} of {pages}
        </span>
        <button
          onClick={() => fetchPage(Math.min(pages || 1, page + 1))}
          disabled={page >= pages}
          className="px-3 py-1 rounded border"
        >
          Next
        </button>
      </div>
    </div>
  );
}
