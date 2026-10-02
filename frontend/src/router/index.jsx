import { createHashRouter, Navigate } from 'react-router-dom';
import AdminLayout from '../layouts/AdminLayout';
import Dashboard from '../pages/Dashboard';
import LiveMonitoring from '../pages/LiveMonitoring';
import Events from '../pages/Events';
import Recordings from '../pages/Recordings';
import DetectionZones from '../pages/DetectionZones';
import Settings from '../pages/Settings';
import CameraManagement from '../pages/CameraManagement';
import Storage from '../pages/Storage';

const router = createHashRouter([
  {
    path: '/',
    element: <AdminLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />
      },
      {
        path: 'dashboard',
        element: <Dashboard />
      },
      {
        path: 'cameras',
        element: <LiveMonitoring />
      },
      {
        path: 'camera-management',
        element: <CameraManagement />
      },
      {
        path: 'events',
        element: <Events />
      },
      {
        path: 'recordings',
        element: <Recordings />
      },
      {
        path: 'zones',
        element: <DetectionZones />
      },
      {
        path: 'storage',
        element: <Storage />
      },
      {
        path: 'settings',
        element: <Settings />
      }
    ]
  }
]);

export default router;
