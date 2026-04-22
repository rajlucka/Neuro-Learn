import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes, useSearchParams } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { UserTypeProvider, useUserType } from "@/contexts/UserTypeContext";
import { AppLayout } from "@/components/AppLayout";
import Index from "./pages/Index";
import Progress from "./pages/Progress";
import Practice from "./pages/Practice";
import HistoryPage from "./pages/History";
import Instructor from "./pages/Instructor";
import SettingsPage from "./pages/Settings";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

/**
 * Reads ?student=S01 from the URL and syncs it into UserTypeContext.
 * Also reads ?role=instructor to switch user type automatically.
 * Must be rendered inside BrowserRouter so useSearchParams works.
 */
function UrlParamSync() {
  const [searchParams] = useSearchParams();
  const { setStudentId, setUserType } = useUserType();

  useEffect(() => {
    const student = searchParams.get("student");
    const role    = searchParams.get("role");

    if (student) setStudentId(student.toUpperCase());
    if (role === "instructor") setUserType("instructor");
    if (role === "new")        setUserType("new");
    if (role === "returning")  setUserType("returning");
  }, [searchParams, setStudentId, setUserType]);

  return null;
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <UserTypeProvider>
        <BrowserRouter>
          <UrlParamSync />
          <AppLayout>
            <Routes>
              <Route path="/"          element={<Index />} />
              <Route path="/progress"  element={<Progress />} />
              <Route path="/practice"  element={<Practice />} />
              <Route path="/history"   element={<HistoryPage />} />
              <Route path="/instructor" element={<Instructor />} />
              <Route path="/settings"  element={<SettingsPage />} />
              <Route path="*"          element={<NotFound />} />
            </Routes>
          </AppLayout>
        </BrowserRouter>
      </UserTypeProvider>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;