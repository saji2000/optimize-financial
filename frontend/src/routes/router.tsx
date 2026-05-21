import { createBrowserRouter, Navigate } from "react-router-dom";
import { App } from "../App";
import { AppShell } from "../components/AppShell";
import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";
import { LibraryPage } from "../pages/LibraryPage";
import { TranscriptDetailPage } from "../pages/TranscriptDetailPage";
import { SignalReviewPage } from "../pages/SignalReviewPage";
import { PipelineRunPage } from "../pages/PipelineRunPage";
import { UploadPage } from "../pages/UploadPage";
import { ExportsPage } from "../pages/ExportsPage";
import { AnalyticsPage } from "../pages/AnalyticsPage";

export const router = createBrowserRouter([
  {
    element: <App />,
    children: [
      { path: "/login", element: <LoginPage /> },
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="/dashboard" replace /> },
          { path: "dashboard", element: <DashboardPage /> },
          { path: "transcripts", element: <LibraryPage /> },
          { path: "transcripts/:id", element: <TranscriptDetailPage /> },
          { path: "review", element: <SignalReviewPage /> },
          { path: "pipeline", element: <PipelineRunPage /> },
          { path: "pipeline/:id", element: <PipelineRunPage /> },
          { path: "upload", element: <UploadPage /> },
          { path: "analytics", element: <AnalyticsPage /> },
          { path: "exports", element: <ExportsPage /> },
          { path: "*", element: <Navigate to="/dashboard" replace /> },
        ],
      },
    ],
  },
]);
