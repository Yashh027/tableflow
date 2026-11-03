"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

type MenuItem = {
  id: string;
  category_id: string;
  name: string;
  description: string | null;
  price: string;
  image_url: string | null;
  vegetarian: boolean;
  vegan: boolean;
  available: boolean;
  preparation_time: number | null;
};

type Category = {
  id: string;
  name: string;
  description: string | null;
};

type MenuData = {
  restaurant: {
    id: string;
    name: string;
    slug: string;
    currency: string;
  };
  categories: Category[];
  items: MenuItem[];
};

type CartItem = {
  item: MenuItem;
  quantity: number;
};

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function CustomerMenuContent() {
  const params = useParams<{ restaurantSlug: string }>();
  const searchParams = useSearchParams();

  const slug = params.restaurantSlug;
  const qrToken = searchParams.get("qr");

  const [menu, setMenu] = useState<MenuData | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [guestName, setGuestName] = useState("");
  const [guestToken, setGuestToken] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    async function loadMenu() {
      try {
        const response = await fetch(
          `${API_URL}/api/v1/public/restaurants/${encodeURIComponent(slug)}/menu`
        );

        if (!response.ok) {
          throw new Error("Could not load this restaurant's menu.");
        }

        setMenu(await response.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : "Menu loading failed.");
      } finally {
        setLoading(false);
      }
    }

    loadMenu();
  }, [slug]);

  const filteredItems = useMemo(() => {
    if (!menu) return [];
    if (activeCategory === "all") return menu.items;
    return menu.items.filter(
      (item) => item.category_id === activeCategory
    );
  }, [menu, activeCategory]);

  const total = cart.reduce(
    (sum, entry) => sum + Number(entry.item.price) * entry.quantity,
    0
  );

  function addItem(item: MenuItem) {
    setCart((current) => {
      const existing = current.find((entry) => entry.item.id === item.id);

      if (existing) {
        return current.map((entry) =>
          entry.item.id === item.id
            ? { ...entry, quantity: entry.quantity + 1 }
            : entry
        );
      }

      return [...current, { item, quantity: 1 }];
    });
    setNotice(`${item.name} added to your order`);
  }

  function changeQuantity(itemId: string, change: number) {
    setCart((current) =>
      current
        .map((entry) =>
          entry.item.id === itemId
            ? { ...entry, quantity: entry.quantity + change }
            : entry
        )
        .filter((entry) => entry.quantity > 0)
    );
  }

  async function joinTable() {
    if (!qrToken) {
      setError("Open this menu using your restaurant's table QR code.");
      return;
    }

    if (!guestName.trim()) {
      setError("Enter your name to join the table.");
      return;
    }

    setError("");

    try {
      const response = await fetch(
        `${API_URL}/api/v1/customer/sessions/join`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            qr_token: qrToken,
            guest_name: guestName.trim(),
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not join this table.");
      }

      setGuestToken(data.guest_token);
      setSessionId(data.session_id);
      setNotice("You've joined the table. You can now place your order.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join table.");
    }
  }

  async function placeOrder() {
    if (!guestToken || !sessionId) {
      setError("Join your table before placing an order.");
      return;
    }

    if (cart.length === 0) {
      setError("Your cart is empty.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const response = await fetch(`${API_URL}/api/v1/customer/orders`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${guestToken}`,
        },
        body: JSON.stringify({
          items: cart.map((entry) => ({
            menu_item_id: entry.item.id,
            quantity: entry.quantity,
          })),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Order could not be placed.");
      }

      setCart([]);
      setNotice(`Order placed successfully. Order ID: ${data.id || data.order_id || "confirmed"}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Order submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#faf9f6] text-[#26251f]">
        Loading menu...
      </main>
    );
  }

  if (error && !menu) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#faf9f6] p-6 text-center">
        <div>
          <h1 className="text-2xl font-semibold">Menu unavailable</h1>
          <p className="mt-3 text-stone-600">{error}</p>
        </div>
      </main>
    );
  }

  if (!menu) return null;

  return (
    <main className="min-h-screen bg-[#faf9f6] pb-36 text-[#26251f]">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-800">
              TABLEFLOW
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight">
              {menu.restaurant.name}
            </h1>
            <p className="mt-1 text-sm text-stone-500">
              Explore the menu and order at your table
            </p>
          </div>
          <div className="rounded-full border border-stone-200 px-4 py-2 text-sm">
            {cart.reduce((sum, entry) => sum + entry.quantity, 0)} items
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-6xl px-5 py-8">
        <div className="rounded-2xl bg-[#173d32] p-7 text-white md:p-10">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-200">
            Freshly prepared
          </p>
          <h2 className="mt-3 max-w-xl text-3xl font-semibold md:text-4xl">
            Good food. Great moments.
          </h2>
          <p className="mt-3 max-w-lg text-sm text-emerald-100">
            Browse our menu, add your favourites and place your order.
          </p>
        </div>

        {!guestToken && (
          <div className="mt-7 rounded-2xl border border-stone-200 bg-white p-5">
            <h3 className="font-semibold">Join your table</h3>
            <p className="mt-1 text-sm text-stone-500">
              Enter your name to join the shared table session.
            </p>
            <div className="mt-4 flex flex-col gap-3 sm:flex-row">
              <input
                value={guestName}
                onChange={(event) => setGuestName(event.target.value)}
                placeholder="Your name"
                className="min-w-0 flex-1 rounded-xl border border-stone-300 px-4 py-3 outline-none focus:border-emerald-700"
              />
              <button
                onClick={joinTable}
                className="rounded-xl bg-[#173d32] px-6 py-3 font-medium text-white hover:bg-[#245c4b]"
              >
                Join table
              </button>
            </div>
            {!qrToken && (
              <p className="mt-3 text-xs text-amber-700">
                A table QR link is required to join and place an order.
              </p>
            )}
          </div>
        )}

        {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
        {notice && (
          <p className="mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">
            {notice}
          </p>
        )}

        <div className="mt-9">
          <h2 className="text-2xl font-semibold">Our menu</h2>
          <div className="mt-5 flex gap-2 overflow-x-auto pb-3">
            <button
              onClick={() => setActiveCategory("all")}
              className={`shrink-0 rounded-full px-5 py-2 text-sm ${
                activeCategory === "all"
                  ? "bg-[#173d32] text-white"
                  : "border border-stone-300 bg-white"
              }`}
            >
              All items
            </button>
            {menu.categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setActiveCategory(category.id)}
                className={`shrink-0 rounded-full px-5 py-2 text-sm ${
                  activeCategory === category.id
                    ? "bg-[#173d32] text-white"
                    : "border border-stone-300 bg-white"
                }`}
              >
                {category.name}
              </button>
            ))}
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filteredItems.map((item) => (
              <article
                key={item.id}
                className="overflow-hidden rounded-2xl border border-stone-200 bg-white"
              >
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={item.name}
                    className="h-44 w-full object-cover"
                  />
                ) : (
                  <div className="grid h-44 place-items-center bg-[#e9e7df] text-4xl">
                    ???
                  </div>
                )}
                <div className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-semibold">{item.name}</h3>
                    <span className="whitespace-nowrap font-semibold">
                      {menu.restaurant.currency} {Number(item.price).toFixed(2)}
                    </span>
                  </div>
                  {item.description && (
                    <p className="mt-2 text-sm leading-6 text-stone-500">
                      {item.description}
                    </p>
                  )}
                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-xs text-stone-500">
                      {item.vegetarian ? "Vegetarian" : "Chef's selection"}
                    </span>
                    <button
                      onClick={() => addItem(item)}
                      disabled={!item.available}
                      className="rounded-full bg-[#173d32] px-5 py-2 text-sm font-medium text-white disabled:opacity-40"
                    >
                      Add +
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>

          {filteredItems.length === 0 && (
            <p className="py-12 text-center text-stone-500">
              No items in this category yet.
            </p>
          )}
        </div>
      </section>

      {cart.length > 0 && (
        <div className="fixed inset-x-0 bottom-0 z-20 border-t border-stone-200 bg-white/95 shadow-2xl backdrop-blur">
          <div className="mx-auto max-w-6xl px-5 py-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-semibold">
                  Your order · {cart.reduce((sum, entry) => sum + entry.quantity, 0)} items
                </p>
                <p className="text-sm text-stone-500">
                  Total: {menu.restaurant.currency} {total.toFixed(2)}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setCart([])}
                  className="rounded-xl border border-stone-300 px-4 py-3 text-sm"
                >
                  Clear
                </button>
                <button
                  onClick={placeOrder}
                  disabled={submitting || !guestToken}
                  className="rounded-xl bg-[#173d32] px-6 py-3 font-medium text-white disabled:opacity-40"
                >
                  {submitting ? "Placing order..." : "Place order"}
                </button>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-stone-500">
              {cart.map((entry) => (
                <span key={entry.item.id} className="flex items-center gap-2">
                  {entry.item.name}
                  <button onClick={() => changeQuantity(entry.item.id, -1)}>-</button>
                  {entry.quantity}
                  <button onClick={() => changeQuantity(entry.item.id, 1)}>+</button>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default function CustomerMenuPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center bg-[#faf9f6] text-[#26251f]">
          Loading menu...
        </main>
      }
    >
      <CustomerMenuContent />
    </Suspense>
  );
}