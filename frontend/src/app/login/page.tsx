"use client";

import { FormEvent, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LoginPage() {
  const [restaurantSlug, setRestaurantSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ restaurant_slug: restaurantSlug, email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed. Check your credentials.");
      }

      if (!data.access_token) {
        throw new Error("The login response did not contain an access token.");
      }

      sessionStorage.setItem("tableflow_token", data.access_token);

      const profileResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      });

      if (!profileResponse.ok) {
        throw new Error("Login succeeded, but the user profile could not be loaded.");
      }

      const profile = await profileResponse.json();
      const role = String(profile.role || "").toLowerCase();

      if (role === "kitchen" || role === "chef") {
        window.location.href = "/kitchen/dashboard";
      } else if (role === "admin" || role === "owner" || role === "manager") {
        window.location.href = "/admin/dashboard";
      } else {
        window.location.href = "/staff/dashboard";
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to log in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#f5f6f4] px-5 py-10">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-bold tracking-[0.25em] text-emerald-800">
          TABLEFLOW
        </p>
        <h1 className="mt-4 text-2xl font-semibold text-slate-900">
          Restaurant workspace
        </h1>
        <p className="mt-2 text-sm text-slate-500">
          Sign in to manage restaurant operations.
        </p>

        <form onSubmit={handleLogin} className="mt-8 space-y-5">
                    <div>
            <label htmlFor="restaurantSlug" className="mb-2 block text-sm font-medium">
              Restaurant slug
            </label>
            <input
              id="restaurantSlug"
              required
              value={restaurantSlug}
              onChange={(event) => setRestaurantSlug(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-emerald-700"
              placeholder="your-restaurant"
            />
          </div><div>
            <label htmlFor="email" className="mb-2 block text-sm font-medium">
              Email address
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-emerald-700"
              placeholder="you@restaurant.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="mb-2 block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-emerald-700"
              placeholder="Enter your password"
            />
          </div>

          {error && (
            <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-[#173d32] px-5 py-3 font-medium text-white hover:bg-[#245c4b] disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-400">
          Secure restaurant operations workspace
        </p>
      </div>
    </main>
  );
}