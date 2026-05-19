import { createBrowserRouter } from "react-router-dom";

import { App } from "../App";
import { DashboardPage } from "../pages/DashboardPage";
import { PipelineRunsPage } from "../pages/PipelineRunsPage";
import { SignalReviewPage } from "../pages/SignalReviewPage";
import { TranscriptDetailPage } from "../pages/TranscriptDetailPage";
import { TranscriptListPage } from "../pages/TranscriptListPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "transcripts", element: <TranscriptListPage /> },
      { path: "transcripts/:transcriptId", element: <TranscriptDetailPage /> },
      { path: "review", element: <SignalReviewPage /> },
      { path: "pipeline-runs", element: <PipelineRunsPage /> },
    ],
  },
]);

