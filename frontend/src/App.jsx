import { Routes, Route } from "react-router-dom";
import { Authenticator } from "@aws-amplify/ui-react";

import Landing from "./pages/Landing.jsx";
import Connect from "./pages/Connect.jsx";
import Dashboard from "./pages/Dashboard.jsx";

function Protected({ Component }) {
  return (
    <Authenticator>
      {({ signOut, user }) => <Component signOut={signOut} user={user} />}
    </Authenticator>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/connect" element={<Protected Component={Connect} />} />
      <Route path="/dashboard" element={<Protected Component={Dashboard} />} />
    </Routes>
  );
}
