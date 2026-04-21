import { Settings as SettingsIcon } from "lucide-react";

const SettingsPage = () => (
  <div className="space-y-6">
    <h1 className="font-heading font-bold text-2xl flex items-center gap-3">
      <SettingsIcon className="h-6 w-6" /> Settings
    </h1>
    <div className="glass-card p-6">
      <p className="text-muted-foreground">Settings panel coming soon. Configure your learning preferences, notification schedule, and account details here.</p>
    </div>
  </div>
);

export default SettingsPage;
