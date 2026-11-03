"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { QRCodeSVG } from "qrcode.react";

const API = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
type Category = { id: string; name: string; description?: string | null };
type Item = { id: string; category_id: string; name: string; description?: string | null; price: string; is_vegetarian: boolean; is_vegan: boolean; is_available: boolean; preparation_time_minutes: number };
type Table = { id: string; table_number: string; capacity: number; is_active: boolean };
type Order = { order_id: string; status: string; total_amount: string; special_instructions?: string | null; created_at?: string; items: { name: string; quantity: number }[] };

export default function AdminDashboardPage() {
  const [token, setToken] = useState("");
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("Restaurant");
  const [categories, setCategories] = useState<Category[]>([]);
  const [items, setItems] = useState<Item[]>([]);
  const [tables, setTables] = useState<Table[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [categoryName, setCategoryName] = useState("");
  const [itemName, setItemName] = useState("");
  const [itemPrice, setItemPrice] = useState("");
  const [itemCategory, setItemCategory] = useState("");
  const [tableNumber, setTableNumber] = useState("");
  const [tableCapacity, setTableCapacity] = useState("4");
  const [qrUrl, setQrUrl] = useState("");
  const [qrLabel, setQrLabel] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function request(path: string, init: RequestInit = {}) {
    const response = await fetch(`${API}${path}`, { ...init, headers: { Authorization: `Bearer ${token}`, ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    return data;
  }

  async function refresh() {
    if (!token) return;
    setError("");
    try {
      const [profile, cats, menuItems, diningTables, orderRows] = await Promise.all([
        request("/api/v1/auth/me"), request("/api/v1/menu/categories"), request("/api/v1/menu/items"), request("/api/v1/management/tables"), request("/api/v1/staff/orders")
      ]);
      setName(profile.name || "Restaurant owner");
      setSlug(profile.restaurant?.slug || "");
      setCategories(cats); setItems(menuItems); setTables(diningTables); setOrders(orderRows);
      if (!itemCategory && cats[0]) setItemCategory(cats[0].id);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load management data"); }
  }

  useEffect(() => { const t = sessionStorage.getItem("tableflow_token"); if (!t) { window.location.href = "/login"; return; } setToken(t); }, []);
  useEffect(() => { if (token) void refresh(); }, [token]);

  async function createCategory(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { await request("/api/v1/menu/categories", { method: "POST", body: JSON.stringify({ name: categoryName.trim(), display_order: categories.length }) }); setCategoryName(""); setNotice("Category created"); await refresh(); }
    catch (x) { setError(x instanceof Error ? x.message : "Category creation failed"); } finally { setBusy(false); }
  }
  async function createItem(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { await request("/api/v1/menu/items", { method: "POST", body: JSON.stringify({ category_id: itemCategory, name: itemName.trim(), price: Number(itemPrice), is_vegetarian: true, is_vegan: false, preparation_time_minutes: 15 }) }); setItemName(""); setItemPrice(""); setNotice("Menu item created"); await refresh(); }
    catch (x) { setError(x instanceof Error ? x.message : "Item creation failed"); } finally { setBusy(false); }
  }
  async function createTable(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try {
      const data = await request("/api/v1/tables", { method: "POST", body: JSON.stringify({ table_number: tableNumber.trim(), capacity: Number(tableCapacity) }) });
      const profile = await request("/api/v1/auth/me");
      const restaurantSlug = profile.restaurant?.slug || slug;
      const url = `${window.location.origin}/menu/${encodeURIComponent(restaurantSlug)}?qr=${encodeURIComponent(data.qr_token)}`;
      setQrUrl(url); setQrLabel(`Table ${data.table_number}`); setTableNumber(""); setNotice("Table created. Download or save this QR now; the secret token is shown only once."); await refresh();
    } catch (x) { setError(x instanceof Error ? x.message : "Table creation failed"); } finally { setBusy(false); }
  }
  async function toggleAvailability(item: Item) {
    try { await request(`/api/v1/menu/items/${item.id}/availability`, { method: "PATCH", body: JSON.stringify({ is_available: !item.is_available }) }); await refresh(); }
    catch (x) { setError(x instanceof Error ? x.message : "Update failed"); }
  }
  function logout() { sessionStorage.removeItem("tableflow_token"); window.location.href = "/login"; }
  const pending = useMemo(() => orders.filter(o => ["pending", "accepted", "preparing", "ready"].includes(o.status)).length, [orders]);

  return <main className="min-h-screen bg-[#f5f7f5] text-slate-900">
    <header className="sticky top-0 z-20 border-b bg-white"><div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4"><div><p className="text-xs font-bold tracking-[.22em] text-emerald-800">TABLEFLOW</p><h1 className="text-xl font-semibold">Restaurant workspace</h1></div><div className="flex items-center gap-3"><span className="hidden text-sm text-slate-500 sm:block">{name}</span><button onClick={logout} className="rounded-lg border px-4 py-2 text-sm">Log out</button></div></div></header>
    <div className="mx-auto max-w-7xl space-y-7 px-5 py-8">
      <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-3xl font-bold">Operations overview</h2><p className="mt-1 text-sm text-slate-500">Manage your menu, tables, QR codes and live orders.</p></div><button onClick={() => void refresh()} className="rounded-lg bg-[#173d32] px-4 py-2.5 text-sm font-semibold text-white">Refresh data</button></div>
      {error && <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}{notice && <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}
      <section className="grid gap-4 sm:grid-cols-3"><Stat label="Menu items" value={items.length}/><Stat label="Dining tables" value={tables.length}/><Stat label="Active orders" value={pending}/></section>
      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border bg-white p-5"><h3 className="text-lg font-semibold">Menu categories</h3><form onSubmit={createCategory} className="mt-4 flex gap-2"><input required minLength={2} value={categoryName} onChange={e=>setCategoryName(e.target.value)} placeholder="e.g. Starters" className="min-w-0 flex-1 rounded-lg border px-3 py-2"/><button disabled={busy} className="rounded-lg bg-[#173d32] px-4 py-2 text-sm font-semibold text-white">Add</button></form><div className="mt-4 space-y-2">{categories.map(c=><div key={c.id} className="rounded-lg bg-slate-50 px-3 py-2 text-sm">{c.name}</div>)}{!categories.length&&<p className="text-sm text-slate-500">No categories yet.</p>}</div></div>
        <div className="rounded-2xl border bg-white p-5"><h3 className="text-lg font-semibold">Add menu item</h3><form onSubmit={createItem} className="mt-4 grid gap-3"><input required minLength={2} value={itemName} onChange={e=>setItemName(e.target.value)} placeholder="Dish name" className="rounded-lg border px-3 py-2"/><input required type="number" min="0.01" step="0.01" value={itemPrice} onChange={e=>setItemPrice(e.target.value)} placeholder="Price (INR)" className="rounded-lg border px-3 py-2"/><select required value={itemCategory} onChange={e=>setItemCategory(e.target.value)} className="rounded-lg border px-3 py-2"><option value="">Choose category</option>{categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select><button disabled={busy||!categories.length} className="rounded-lg bg-[#173d32] px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-40">Save menu item</button></form></div>
      </section>
      <section className="rounded-2xl border bg-white p-5"><div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-lg font-semibold">Menu availability</h3><Link href={slug ? `/menu/${slug}` : "/login"} target="_blank" className="text-sm font-medium text-emerald-800 underline">Preview customer menu</Link></div><div className="mt-4 divide-y">{items.map(i=><div key={i.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div><p className="font-medium">{i.name}</p><p className="text-sm text-slate-500">₹{Number(i.price).toFixed(2)} · {categories.find(c=>c.id===i.category_id)?.name || "Uncategorised"}</p></div><button onClick={()=>void toggleAvailability(i)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${i.is_available?"bg-emerald-100 text-emerald-800":"bg-slate-100 text-slate-600"}`}>{i.is_available?"Available · turn off":"Unavailable · turn on"}</button></div>)}{!items.length&&<p className="py-4 text-sm text-slate-500">Add a category and your first dish to populate the menu.</p>}</div></section>
      <section className="grid gap-5 lg:grid-cols-2"><div className="rounded-2xl border bg-white p-5"><h3 className="text-lg font-semibold">Tables & QR codes</h3><form onSubmit={createTable} className="mt-4 grid grid-cols-[1fr_100px_auto] gap-2"><input required value={tableNumber} onChange={e=>setTableNumber(e.target.value)} placeholder="Table 1" className="min-w-0 rounded-lg border px-3 py-2"/><input required type="number" min="1" max="30" value={tableCapacity} onChange={e=>setTableCapacity(e.target.value)} className="rounded-lg border px-3 py-2"/><button disabled={busy} className="rounded-lg bg-[#173d32] px-3 py-2 text-sm font-semibold text-white">Create</button></form><div className="mt-4 space-y-2">{tables.map(t=><div key={t.id} className="flex justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"><span>{t.table_number} · {t.capacity} seats</span><span className={t.is_active?"text-emerald-700":"text-slate-400"}>{t.is_active?"Active":"Inactive"}</span></div>)}{!tables.length&&<p className="text-sm text-slate-500">No tables created.</p>}</div>{qrUrl&&<div className="mt-5 flex flex-col items-center rounded-xl border bg-white p-5 text-center"><QRCodeSVG value={qrUrl} size={190}/><p className="mt-3 font-semibold">{qrLabel}</p><p className="mt-1 max-w-sm break-all text-xs text-slate-500">{qrUrl}</p><div className="mt-3 flex gap-2"><button onClick={()=>navigator.clipboard.writeText(qrUrl)} className="rounded-lg border px-3 py-2 text-sm">Copy link</button><button onClick={()=>{const svg=document.querySelector("#tableflow-admin-qr svg");if(!svg)return;const blob=new Blob([new XMLSerializer().serializeToString(svg)],{type:"image/svg+xml"});const u=URL.createObjectURL(blob);const a=document.createElement("a");a.href=u;a.download=`${qrLabel.replaceAll(" ","-")}.svg`;a.click();URL.revokeObjectURL(u);}} className="rounded-lg bg-[#173d32] px-3 py-2 text-sm text-white">Download QR</button></div><div id="tableflow-admin-qr" className="hidden"><QRCodeSVG value={qrUrl}/></div></div>}</div>
        <div className="rounded-2xl border bg-white p-5"><div className="flex items-center justify-between"><h3 className="text-lg font-semibold">Live order overview</h3><span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">{pending} active</span></div><div className="mt-4 space-y-3">{orders.slice(0,8).map(o=><div key={o.order_id} className="rounded-lg border p-3"><div className="flex justify-between gap-3"><span className="font-medium">#{o.order_id.slice(0,8)}</span><span className="text-xs font-semibold uppercase text-emerald-800">{o.status}</span></div><p className="mt-1 text-sm text-slate-500">{o.items?.map(x=>`${x.quantity}× ${x.name}`).join(", ")}</p><p className="mt-1 text-sm font-semibold">₹{Number(o.total_amount).toFixed(2)}</p></div>)}{!orders.length&&<p className="text-sm text-slate-500">Orders will appear here when customers place them.</p>}</div></div></section>
      <section className="flex flex-wrap gap-3"><Link href="/staff/dashboard" className="rounded-lg border bg-white px-4 py-3 text-sm font-semibold">Open staff workspace →</Link><Link href="/kitchen/dashboard" className="rounded-lg border bg-white px-4 py-3 text-sm font-semibold">Open kitchen display →</Link><Link href="/admin/qr" className="rounded-lg border bg-white px-4 py-3 text-sm font-semibold">QR utility →</Link></section>
      <p className="text-xs text-slate-500">Note: QR token is displayed only when a table is created. Save/download the QR immediately. Online payment processing is not enabled yet.</p>
    </div>
  </main>;
}
function Stat({label,value}:{label:string;value:number}) { return <div className="rounded-2xl border bg-white p-5"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-3xl font-bold">{value}</p></div>; }
