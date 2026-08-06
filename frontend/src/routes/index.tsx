import { Suspense, lazy } from "react";
import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RouteFallback } from "@/components/layout/RouteFallback";

// Route-level code splitting: each page is its own chunk so the initial
// bundle only carries the dashboard and shared shell.
const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);
const PostsPage = lazy(() =>
  import("@/pages/PostsPage").then((m) => ({ default: m.PostsPage })),
);
const CommentsPage = lazy(() =>
  import("@/pages/CommentsPage").then((m) => ({ default: m.CommentsPage })),
);
const AccountsPage = lazy(() =>
  import("@/pages/AccountsPage").then((m) => ({ default: m.AccountsPage })),
);
const SyncRunsPage = lazy(() =>
  import("@/pages/SyncRunsPage").then((m) => ({ default: m.SyncRunsPage })),
);
const SettingsPage = lazy(() =>
  import("@/pages/SettingsPage").then((m) => ({ default: m.SettingsPage })),
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Suspense fallback={<RouteFallback />}><DashboardPage /></Suspense> },
      { path: "posts", element: <Suspense fallback={<RouteFallback />}><PostsPage /></Suspense> },
      { path: "comments", element: <Suspense fallback={<RouteFallback />}><CommentsPage /></Suspense> },
      { path: "accounts", element: <Suspense fallback={<RouteFallback />}><AccountsPage /></Suspense> },
      { path: "sync-runs", element: <Suspense fallback={<RouteFallback />}><SyncRunsPage /></Suspense> },
      { path: "settings", element: <Suspense fallback={<RouteFallback />}><SettingsPage /></Suspense> },
    ],
  },
]);
