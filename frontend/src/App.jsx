import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Network } from './pages/Network';
import { PersonDetail } from './pages/PersonDetail';
import { Admin } from './pages/Admin';
import { Login } from './pages/Login';
import { AuthProvider, useAuth } from './hooks/useAuth';

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div style={{ padding: '2rem', color: 'var(--text-secondary)' }}>Loading...</div>;
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

function AppContent() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/network" element={<Network />} />
                <Route path="/person/:id" element={<PersonDetail />} />
                <Route path="/admin" element={<Admin />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
