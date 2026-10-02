import { RouterProvider } from 'react-router-dom';
import router from './router';
import { ThemeProvider } from './context/ThemeProvider';

function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="smart-vms-theme">
      <div className="min-h-screen bg-background text-foreground transition-colors duration-300">
        <RouterProvider router={router} />
      </div>
    </ThemeProvider>
  );
}

export default App;
