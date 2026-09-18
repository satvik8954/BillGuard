import { fetchAuthSession } from "aws-amplify/auth";

const API_BASE = "https://jjuvv88jpl.execute-api.ap-south-1.amazonaws.com/";

async function authHeader() {
  const session = await fetchAuthSession();
  const idToken = session.tokens?.idToken?.toString();
  return idToken ? { Authorization: `Bearer ${idToken}` } : {};
}

async function request(method, path, body) {
  const headers = { "Content-Type": "application/json", ...(await authHeader()) };
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    const message = data.error || `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

export const api = {
  connectInit: () => request("POST", "connect/init"),
  connectVerify: (roleArn) => request("POST", "connect/verify", { roleArn }),
  getFindings: () => request("GET", "findings"),
  getScanLatest: () => request("GET", "scan/latest"),
  startScan: () => request("POST", "scan"),
};
