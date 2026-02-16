import { useLocation } from 'react-router-dom';

interface HeaderProps {
  title?: string;
  description?: string;
}

const routeTitles: Record<string, { title: string; description: string }> = {
  '/': {
    title: 'Dashboard',
    description: 'Genel bakış ve önemli metrikler'
  },
  '/games': {
    title: 'Oyunlar',
    description: 'Steam oyunları ve detaylı istatistikler'
  },
  '/causal-analysis': {
    title: 'Nedensel Analiz',
    description: 'Difference-in-Differences (DiD) modeli ile fiyat etkisi analizi'
  },
  '/survival-analysis': {
    title: 'Survival Analizi',
    description: 'Kaplan-Meier ve Cox PH ile oyuncu retention analizi'
  },
  '/data-status': {
    title: 'Veri Durumu',
    description: 'ETL pipeline durumu ve veri kalitesi metrikleri'
  },
};

export default function Header({ title, description }: HeaderProps) {
  const location = useLocation();
  
  // Use provided title/description or get from route
  const pageInfo = title && description 
    ? { title, description }
    : routeTitles[location.pathname] || { title: 'Page', description: '' };

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="max-w-7xl">
        <h1 className="text-2xl font-bold text-gray-900">{pageInfo.title}</h1>
        {pageInfo.description && (
          <p className="mt-1 text-sm text-gray-600">{pageInfo.description}</p>
        )}
      </div>
    </div>
  );
}
