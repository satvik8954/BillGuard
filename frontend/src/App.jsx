import { Routes, Route } from "react-router-dom";
import { Authenticator } from "@aws-amplify/ui-react";

import Landing from "./pages/Landing.jsx";
import Connect from "./pages/Connect.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import ConnectionGate from "./components/ConnectionGate.jsx";

function Protected({ Component, requires }) {
  return (
    <Authenticator>
      {({ signOut, user }) => (
        <ConnectionGate requires={requires}>
          <Component signOut={signOut} user={user} />
        </ConnectionGate>
      )}
    </Authenticator>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/connect" element={<Protected Component={Connect} requires="not-connected" />} />
      <Route path="/dashboard" element={<Protected Component={Dashboard} requires="connected" />} />
    </Routes>
  );
}
