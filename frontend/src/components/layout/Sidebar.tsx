import { Link, useLocation } from 'react-router-dom';

interface NavItem {
  name: string;
  path: string;
  icon: string;
}

const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/', icon: '🏠' },
  { name: 'Oyunlar', path: '/games', icon: '🎮' },
  { name: 'Nedensel Analiz', path: '/causal-analysis', icon: '📊' },
  { name: 'Survival Analizi', path: '/survival-analysis', icon: '⏱️' },
  { name: 'Veri Durumu', path: '/data-status', icon: '💾' },
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <div className="flex flex-col w-64 bg-gray-900 text-white h-screen fixed left-0 top-0">
      {/* Logo/Title */}
      <div className="flex items-center justify-center h-16 bg-gray-800 border-b border-gray-700">
        <span className="text-3xl mr-2">🔬</span>
        <h1 className="text-xl font-bold">Steam Analytics</h1>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-3">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`
                    flex items-center px-4 py-3 rounded-lg transition-colors duration-200
                    ${isActive 
                      ? 'bg-blue-600 text-white' 
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                    }
                  `}
                >
                  <span className="text-xl mr-3">{item.icon}</span>
                  <span className="font-medium">{item.name}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <div className="text-xs text-gray-400 text-center">
          <p>Steam Games Analysis</p>
          <p className="mt-1">v1.0.0</p>
        </div>
      </div>
    </div>
  );
}
