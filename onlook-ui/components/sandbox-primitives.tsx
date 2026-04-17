"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { formatScalarValue } from "@/lib/display";
import { sandboxRoutes } from "@/lib/sandbox-routes";

export type SurfaceBadge = {
  label: string;
  value: string;
  tone?: "neutral" | "accent" | "success" | "warning";
};

type SurfaceIntroProps = {
  title: string;
  detail: string;
  badges?: SurfaceBadge[];
  children?: ReactNode;
};

export function SurfaceIntro({
  title,
  detail,
  badges = [],
  children,
}: SurfaceIntroProps) {
  const pathname = usePathname();

  return (
    <section className="rounded-[2rem] border border-slate-200 bg-white/85 p-5 shadow-sm backdrop-blur">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-3xl">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
            Onlook Review Sandbox
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
            {title}
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">{detail}</p>
        </div>
        {children ? <div className="xl:min-w-[24rem]">{children}</div> : null}
      </div>

      <nav className="mt-5 flex flex-wrap gap-2" aria-label="Sandbox routes">
        {sandboxRoutes.map((route) => {
          const isActive = route.href === pathname;
          return (
            <Link
              key={route.href}
              href={route.href}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                isActive
                  ? "border-sky-600 bg-sky-600 text-white shadow-sm"
                  : "border-slate-200 bg-slate-50 text-slate-700 hover:border-slate-300 hover:bg-slate-100"
              }`}
            >
              {route.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-5">
        {sandboxRoutes.map((route) => {
          const isActive = route.href === pathname;
          return (
            <div
              key={`${route.href}-detail`}
              className={`rounded-2xl border px-3 py-3 text-xs leading-5 ${
                isActive
                  ? "border-sky-200 bg-sky-50 text-sky-900"
                  : "border-slate-200 bg-slate-50 text-slate-600"
              }`}
            >
              <div className="font-semibold">{route.label}</div>
              <div className="mt-1">{route.detail}</div>
            </div>
          );
        })}
      </div>

      {badges.length > 0 ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {badges.map((badge) => (
            <span
              key={`${badge.label}-${badge.value}`}
              className={`rounded-full border px-3 py-1 text-xs font-medium ${badgeClassName(
                badge.tone ?? "neutral",
              )}`}
            >
              {badge.label}: {badge.value}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
}

type PanelProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = "",
}: PanelProps) {
  return (
    <section
      className={`rounded-[1.75rem] border border-slate-200 bg-white/80 p-5 shadow-sm ${className}`.trim()}
    >
      <div className="flex flex-col gap-3 border-b border-slate-100 pb-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          {subtitle ? (
            <p className="mt-1 text-sm leading-6 text-slate-600">{subtitle}</p>
          ) : null}
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
      <div className="pt-4">{children}</div>
    </section>
  );
}

export function NoticeList({
  title,
  items,
  emptyMessage,
}: {
  title: string;
  items: string[];
  emptyMessage: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        {title}
      </div>
      {items.length > 0 ? (
        <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
          {items.map((item) => (
            <li key={item} className="rounded-xl bg-white/80 px-3 py-2">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-3 rounded-xl bg-white/80 px-3 py-2 text-sm text-slate-500">
          {emptyMessage}
        </div>
      )}
    </div>
  );
}

export function DetailGrid({
  items,
  columns = 2,
}: {
  items: Array<{ label: string; value: ReactNode }>;
  columns?: 1 | 2 | 3 | 4;
}) {
  const className =
    columns === 1
      ? "grid gap-3"
      : columns === 2
        ? "grid gap-3 md:grid-cols-2"
        : columns === 3
          ? "grid gap-3 md:grid-cols-2 xl:grid-cols-3"
          : "grid gap-3 md:grid-cols-2 xl:grid-cols-4";

  return (
    <div className={className}>
      {items.map((item) => (
        <div
          key={`${item.label}`}
          className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-3"
        >
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            {item.label}
          </div>
          <div className="mt-2 text-sm leading-6 text-slate-800">{item.value}</div>
        </div>
      ))}
    </div>
  );
}

export function TabStrip({
  tabs,
  activeTab,
  onChange,
}: {
  tabs: Array<{ tabId: string; label: string; disabled?: boolean }>;
  activeTab: string;
  onChange: (tabId: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map((tab) => {
        const isActive = tab.tabId === activeTab;
        return (
          <button
            key={tab.tabId}
            type="button"
            disabled={tab.disabled}
            onClick={() => onChange(tab.tabId)}
            className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
              tab.disabled
                ? "cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400"
                : isActive
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}

export function JsonBlock({
  value,
  className = "",
}: {
  value: unknown;
  className?: string;
}) {
  return (
    <pre
      className={`overflow-x-auto rounded-2xl border border-slate-200 bg-slate-950 px-4 py-4 text-xs leading-6 text-slate-100 ${className}`.trim()}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 px-5 py-8 text-center">
      <div className="text-sm font-semibold text-slate-800">{title}</div>
      <div className="mt-2 text-sm leading-6 text-slate-500">{detail}</div>
    </div>
  );
}

export function StatusBanner({
  message,
  tone,
}: {
  message: string;
  tone: "info" | "error" | "success";
}) {
  const toneClasses =
    tone === "error"
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : tone === "success"
        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
        : "border-sky-200 bg-sky-50 text-sky-700";

  return (
    <div className={`rounded-2xl border px-4 py-3 text-sm ${toneClasses}`}>
      {message}
    </div>
  );
}

export function renderScalarGrid(
  data: Record<string, unknown>,
): Array<{ label: string; value: string }> {
  return Object.entries(data).map(([key, value]) => ({
    label: key,
    value: formatScalarValue(value),
  }));
}

function badgeClassName(tone: SurfaceBadge["tone"]): string {
  switch (tone) {
    case "accent":
      return "border-sky-200 bg-sky-50 text-sky-800";
    case "success":
      return "border-emerald-200 bg-emerald-50 text-emerald-800";
    case "warning":
      return "border-amber-200 bg-amber-50 text-amber-800";
    default:
      return "border-slate-200 bg-slate-100 text-slate-700";
  }
}
