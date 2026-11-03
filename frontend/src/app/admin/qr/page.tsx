"use client";

import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";

export default function QRGeneratorPage() {
  const [slug, setSlug] = useState("");
  const [table, setTable] = useState("");
  const [token, setToken] = useState("");

  const customerUrl =
    typeof window !== "undefined" && slug.trim() && token.trim()
      ? `${window.location.origin}/menu/${encodeURIComponent(slug.trim())}?qr=${encodeURIComponent(token.trim())}`
      : "";

  function downloadQR() {
    const svg = document.querySelector("#tableflow-qr svg");
    if (!svg) return;

    const blob = new Blob(
      [new XMLSerializer().serializeToString(svg)],
      { type: "image/svg+xml;charset=utf-8" }
    );

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `tableflow-${table.trim() || "table"}.svg`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function copyUrl() {
    if (customerUrl) await navigator.clipboard.writeText(customerUrl);
  }

  return (
    <main className="min-h-screen bg-slate-950 p-6 text-white">
      <div className="mx-auto max-w-3xl space-y-8">
        <header>
          <p className="text-sm font-semibold uppercase tracking-widest text-emerald-400">
            TableFlow
          </p>
          <h1 className="mt-2 text-3xl font-bold">QR & NFC Generator</h1>
          <p className="mt-2 text-slate-400">
            Generate customer access links for restaurant tables.
          </p>
        </header>

        <section className="grid gap-6 rounded-2xl border border-slate-800 bg-slate-900 p-6 md:grid-cols-2">
          <div className="space-y-4">
            <label className="block text-sm text-slate-300">
              Restaurant slug
              <input
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="restaurant-name"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 p-3"
              />
            </label>

            <label className="block text-sm text-slate-300">
              Table label
              <input
                value={table}
                onChange={(e) => setTable(e.target.value)}
                placeholder="Table 01"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 p-3"
              />
            </label>

            <label className="block text-sm text-slate-300">
              Original QR token
              <input
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste original table token"
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 p-3"
              />
            </label>

            <p className="text-xs text-amber-400">
              Use the original token returned when the table was created, not
              its stored hash.
            </p>
          </div>

          <div className="flex flex-col items-center justify-center rounded-xl bg-white p-6 text-slate-950">
            {customerUrl ? (
              <>
                <div id="tableflow-qr">
                  <QRCodeSVG value={customerUrl} size={220} />
                </div>
                <p className="mt-4 font-semibold">{table || "Restaurant Table"}</p>
                <p className="mt-2 break-all text-center text-xs">{customerUrl}</p>
              </>
            ) : (
              <p className="text-center text-sm text-slate-500">
                Enter restaurant slug and QR token to generate a QR code.
              </p>
            )}
          </div>
        </section>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={downloadQR}
            disabled={!customerUrl}
            className="rounded-lg bg-emerald-500 px-5 py-3 font-semibold text-slate-950 disabled:opacity-40"
          >
            Download QR (SVG)
          </button>
          <button
            onClick={copyUrl}
            disabled={!customerUrl}
            className="rounded-lg border border-slate-700 px-5 py-3 disabled:opacity-40"
          >
            Copy NFC URL
          </button>
        </div>
      </div>
    </main>
  );
}