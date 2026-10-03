import Dashboard from "../components/Dashboard";
import pilot from "../lib/energy-pilot.json";

export const dynamic = "force-dynamic";

export default function Home() {
  const recordedDemo = process.env.TREASURY_DEMO_MODE === "recorded"
    || (process.env.VERCEL === "1" && !(process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL));
  return <Dashboard pilot={pilot} recordedDemo={recordedDemo} />;
}
