"use client";

import { useCallback, useEffect, useState } from "react";

type Row = Record<string, unknown>;

type DashboardProps = {
  mode: "staff" | "kitchen" | "admin";
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getRows(data: unknown): Row[] {
  if (Array.isArray(data)) return data as Row[];

  if (data && typeof data === "object") {
    const object = data as Record<string, unknown>;

    for (const key of ["items", "orders", "requests", "results", "data"]) {
      if (Array.isArray(object[key])) return object[key] as Row[];
    }
  }

  return [];
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function OperationsDashboard({ mode }: DashboardProps) {
  const [token, setToken] = useState("");
  const [profile, setProfile] = useState<Row | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [requests, setRequests] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const title =
    mode === "staff"
      ? "Staff dashboard"
      : mode === "kitchen"
        ? "Kitchen display"
        : "Restaurant admin";

  const loadDashboard = useCallback(async (accessToken: string) => {
    setLoading(true);
    setError("");

    const headers = { Authorization: `Bearer ${accessToken}` };

    try {
      const profileResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers,
      });

      if (!profileResponse.ok) {
        throw new Error("Your session has expired. Please log in again.");
      }

      setProfile(await profileResponse.json());

      if (mode === "staff") {
        const [ordersResponse, requestsResponse] = await Promise.all([
          fetch(`${API_URL}/api/v1/staff/orders`, { headers }),
          fetch(`${API_URL}/api/v1/staff/service-requests`, { headers }),
        ]);

        if (ordersResponse.ok) {
          setRows(getRows(await ordersResponse.json()));
        }

        if (requestsResponse.ok) {
          setRequests(getRows(await requestsResponse.json()));
        }
      }

      if (mode === "kitchen") {
        const response = await fetch(`${API_URL}/api/v1/kitchen/queue`, {
          headers,
        });

        if (!response.ok) {
          throw new Error("Could not load the kitchen queue.");
        }

        setRows(getRows(await response.json()));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Dashboard loading failed.");
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    const savedToken = sessionStorage.getItem("tableflow_token");

    if (!savedToken) {
      window.location.href = "/login";
      return;
    }

    setToken(savedToken);
    void loadDashboard(savedToken);
  }, [loadDashboard]);

  async function updateOrder(orderId: string, status: string) {
    try {
      const response = await fetch(
        `${API_URL}/api/v1/staff/orders/${orderId}/status`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status }),
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Could not update order status.");
      }

      setNotice(`Order updated to ${status}.`);
      await loadDashboard(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed.");
    }
  }

  async function updateRequest(requestId: string, status: string) {
    try {
      const response = await fetch(
        `${API_URL}/api/v1/staff/service-requests/${requestId}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ status }),
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Could not update service request.");
      }

      setNotice(`Service request updated to ${status}.`);
      await loadDashboard(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed.");
    }
  }

  function logout() {
    sessionStorage.removeItem("tableflow_token");
    window.location.href = "/login";
  }

  const name =
    display(profile?.full_name || profile?.name || profile?.email);

  return (
    <main className="min-h-screen bg-[#f5f6f4] text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div>
            <p className="text-xs font-bold tracking-[0.2em] text-emerald-800">
              TABLEFLOW
            </p>
            <h1 className="mt-1 text-xl font-semibold">{title}</h1>
          </div>

          <div className="flex items-center gap-4">
            <span className="hidden text-sm text-slate-500 sm:block">{name}</span>
            <button
              onClick={logout}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-5 py-8">
        <div className="mb-7 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold">Overview</h2>
            <p className="mt-1 text-sm text-slate-500">
              Restaurant operations and live activity
            </p>
          </div>

          <button
            onClick={() => void loadDashboard(token)}
            disabled={loading || !token}
            className="rounded-lg bg-[#173d32] px-4 py-2.5 text-sm font-medium text-white hover:bg-[#245c4b] disabled:opacity-50"
          >
            Refresh data
          </button>
        </div>

        {error && (
          <div className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {notice && (
          <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            {notice}
          </div>
        )}

        {loading ? (
          <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-500">
            Loading dashboard...
          </div>
        ) : (
          <>
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <p className="text-sm text-slate-500">Account</p>
                <p className="mt-2 text-lg font-semibold">{name}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {display(profile?.role || "Authenticated user")}
                </p>
              </div>

              {mode !== "admin" && (
                <div className="rounded-xl border border-slate-200 bg-white p-5">
                  <p className="text-sm text-slate-500">
                    {mode === "staff" ? "Orders loaded" : "Kitchen tickets loaded"}
                  </p>
                  <p className="mt-2 text-3xl font-semibold">{rows.length}</p>
                </div>
              )}

              {mode === "staff" && (
                <div className="rounded-xl border border-slate-200 bg-white p-5">
                  <p className="text-sm text-slate-500">Service requests</p>
                  <p className="mt-2 text-3xl font-semibold">{requests.length}</p>
                </div>
              )}
            </section>

            {mode === "admin" && (
              <section className="mt-7 rounded-xl border border-slate-200 bg-white p-6">
                <h3 className="text-lg font-semibold">Management workspace</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Your restaurant account is connected. Use the management
                  sections below as the next modules are completed.
                </p>

                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {[
                    ["Menu management", "Manage categories, dishes and prices"],
                    ["Tables and QR codes", "Manage dining tables and QR links"],
                    ["Staff management", "Manage restaurant team access"],
                    ["Orders", "Review restaurant orders"],
                    ["Billing", "Review bills and payment records"],
                    ["Analytics", "Review restaurant performance"],
                  ].map(([heading, description]) => (
                    <div key={heading} className="rounded-lg border border-slate-200 p-4">
                      <h4 className="font-medium">{heading}</h4>
                      <p className="mt-1 text-sm text-slate-500">{description}</p>
                      <span className="mt-3 inline-block text-xs text-amber-700">
                        Module pending
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {mode !== "admin" && (
              <section className="mt-7 rounded-xl border border-slate-200 bg-white">
                <div className="border-b border-slate-200 px-5 py-4">
                  <h3 className="font-semibold">
                    {mode === "staff" ? "Restaurant orders" : "Kitchen queue"}
                  </h3>
                </div>

                {rows.length === 0 ? (
                  <p className="p-8 text-center text-sm text-slate-500">
                    No records returned by the server.
                  </p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {rows.map((row, index) => {
                      const id = display(row.id || row.order_id || index);
                      const status = display(row.status);
                      const orderItems = Array.isArray(row.items)
                        ? (row.items as Row[])
                        : [];

                      return (
                        <article key={id} className="p-5">
                          <div className="flex flex-wrap items-start justify-between gap-4">
                            <div>
                              <p className="font-semibold">
                                Order #{display(row.id || row.order_id || index + 1)}
                              </p>
                              <p className="mt-1 text-sm text-slate-500">
                                Table: {display(row.table_number || row.table_id)}
                              </p>
                              <p className="mt-1 text-sm text-slate-500">
                                Status: {status}
                              </p>
                            </div>

                            <p className="font-semibold">
                              {display(row.total_amount || row.total || "")}
                            </p>
                          </div>

                          {orderItems.length > 0 && (
                            <p className="mt-3 text-sm text-slate-600">
                              {orderItems.map((item) =>
                                `${display(item.name || item.menu_item_name)} x ${display(item.quantity)}`
                              ).join(", ")}
                            </p>
                          )}

                          {mode === "staff" && (
                            <div className="mt-4 flex flex-wrap gap-2">
                              {["accepted", "preparing", "ready", "served"].map((nextStatus) => (
                                <button
                                  key={nextStatus}
                                  onClick={() => void updateOrder(id, nextStatus)}
                                  className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium capitalize hover:border-emerald-700 hover:text-emerald-800"
                                >
                                  {nextStatus}
                                </button>
                              ))}
                            </div>
                          )}
                        </article>
                      );
                    })}
                  </div>
                )}
              </section>
            )}

            {mode === "staff" && (
              <section className="mt-7 rounded-xl border border-slate-200 bg-white">
                <div className="border-b border-slate-200 px-5 py-4">
                  <h3 className="font-semibold">Service requests</h3>
                </div>

                {requests.length === 0 ? (
                  <p className="p-8 text-center text-sm text-slate-500">
                    No service requests returned by the server.
                  </p>
                ) : (
                  <div className="divide-y divide-slate-100">
                    {requests.map((request, index) => {
                      const id = display(request.id || index);
                      return (
                        <div key={id} className="flex flex-wrap items-center justify-between gap-4 p-5">
                          <div>
                            <p className="font-medium">
                              {display(request.request_type || "Assistance")}
                            </p>
                            <p className="mt-1 text-sm text-slate-500">
                              {display(request.message)}
                            </p>
                            <p className="mt-1 text-xs text-slate-400">
                              Status: {display(request.status)}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {["acknowledged", "in_progress", "resolved"].map((status) => (
                              <button
                                key={status}
                                onClick={() => void updateRequest(id, status)}
                                className="rounded-lg border border-slate-300 px-3 py-2 text-xs capitalize hover:border-emerald-700"
                              >
                                {status.replace("_", " ")}
                              </button>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}