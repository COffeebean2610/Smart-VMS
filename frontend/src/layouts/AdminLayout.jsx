import { useState, useEffect } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Cctv, 
  AlertTriangle, 
  Video, 
  Settings,
  Map,
  Moon,
  Sun,
  Monitor,
  Camera,
  HardDrive
} from 'lucide-react';
import { cn } from '../utils/cn';
import { useTheme } from '../context/ThemeProvider';
import { Button } from '../components/ui/button';
import DbStatusBadge from '../components/DbStatusBadge';
import FirstRunWizard from '../components/FirstRunWizard';
import { getFirstRunStatus } from '../services/systemService';

const sidebarLinks = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Camera Mgmt', path: '/camera-management', icon: Camera },
  { name: 'Live Monitoring', path: '/cameras', icon: Cctv },
  { name: 'Events', path: '/events', icon: AlertTriangle },
  { name: 'Recordings', path: '/recordings', icon: Video },
  { name: 'Detection Zones', path: '/zones', icon: Map },
  { name: 'Storage', path: '/storage', icon: HardDrive },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export default function AdminLayout() {
  const currentTime = new Date().toLocaleString(undefined, { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const [showWizard, setShowWizard] = useState(false);

  useEffect(() => {
    checkFirstRunStatus();
  }, []);

  const checkFirstRunStatus = async () => {
    try {
      const res = await getFirstRunStatus();
      if (res && !res.firstRunCompleted) {
        setShowWizard(true);
      }
    } catch {
      console.error("Failed to fetch first run status");
    }
  };

  const handleWizardComplete = () => {
    setShowWizard(false);
    navigate('/dashboard');
  };

  const toggleTheme = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      {showWizard && <FirstRunWizard onComplete={handleWizardComplete} />}

      {/* Sidebar */}
      <aside className="w-64 shrink-0 border-r border-border bg-card relative">
        <div className="flex h-16 items-center px-6 border-b border-border">
          <Cctv className="h-6 w-6 text-primary mr-3" />
          <span className="font-bold text-lg tracking-tight">Smart VMS</span>
        </div>
        <nav className="flex flex-col gap-1 p-4">
          {sidebarLinks.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.path}
                to={link.path}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive 
                      ? "bg-primary/10 text-primary" 
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {link.name}
              </NavLink>
            );
          })}
        </nav>
        
        {/* Landscape Graphic (CSS gradient) */}
        <div className="absolute bottom-16 left-0 right-0 h-48 opacity-20 pointer-events-none bg-linear-to-t from-green-500/30 via-blue-400/20 to-transparent" />
        
        {/* Collapse button */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border bg-card">
          <Button variant="ghost" className="w-full justify-start text-muted-foreground">
            <Settings className="h-4 w-4 mr-3" />
            Collapse
          </Button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Navbar */}
        <header className="h-16 shrink-0 border-b border-border bg-card flex items-center justify-between px-6">
          <div className="font-semibold text-sm text-muted-foreground">
            Enterprise Management Console
          </div>
          <div className="flex items-center gap-4">
            <DbStatusBadge />
            <Button variant="ghost" size="icon" onClick={toggleTheme} className="rounded-full">
              {theme === 'light' && <Sun className="h-5 w-5" />}
              {theme === 'dark' && <Moon className="h-5 w-5" />}
              {theme === 'system' && <Monitor className="h-5 w-5" />}
            </Button>
            <div className="text-sm text-muted-foreground hidden md:block">
              {currentTime}
            </div>
            <div className="flex items-center gap-2">
              <div className="h-9 w-9 rounded-full bg-primary/20 text-primary flex items-center justify-center border border-primary/30">
                <span className="text-sm font-bold">A</span>
              </div>
              <span className="text-sm font-medium hidden md:block">Admin User</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6 bg-background">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
