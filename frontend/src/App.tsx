import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./components/ProtectedRoute";
import { DatasetEditPage } from "./pages/DatasetEditPage";
import { DatasetUploadPage } from "./pages/DatasetUploadPage";
import { DocumentUploadPage } from "./pages/DocumentUploadPage";
import { LoginPage } from "./pages/LoginPage";
import { LogoutPage } from "./pages/LogoutPage";
import { NewRunPage } from "./pages/NewRunPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ReportPage } from "./pages/ReportPage";
import { RunDetailPage } from "./pages/RunDetailPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
        <Route
          path="/projects/:projectId/datasets/new"
          element={<DatasetUploadPage />}
        />
        <Route
          path="/projects/:projectId/datasets/:datasetId/edit"
          element={<DatasetEditPage />}
        />
        <Route
          path="/projects/:projectId/documents/new"
          element={<DocumentUploadPage />}
        />
        <Route path="/projects/:projectId/runs/new" element={<NewRunPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/runs/:runId/report" element={<ReportPage />} />
        <Route path="/logout" element={<LogoutPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
