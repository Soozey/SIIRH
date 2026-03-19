import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";


export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#07111f] text-slate-100 flex items-center justify-center">
        <div className="rounded-3xl border border-slate-800 bg-slate-950/80 px-8 py-6 shadow-2xl shadow-slate-950/40">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-cyan-400/20 border-t-cyan-400" />
        </div>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}
