import Layout from '../components/layout/Layout';
import KPICard from '../components/cards/KPICard';
import { useDashboardSummary } from '../hooks/useAnalytics';
import { format } from 'date-fns';

export default function Dashboard() {
  const { data: summary, isLoading, error } = useDashboardSummary();

  if (error) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">
            ❌ Veri yüklenirken bir hata oluştu. Lütfen backend servisinin çalıştığından emin olun.
          </p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* KPI Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <KPICard
            title="Toplam Oyun"
            value={summary?.total_games || 0}
            icon="🎮"
            loading={isLoading}
            subtitle={summary?.total_games ? `${summary.total_games} oyun veritabanında` : undefined}
          />
          
          <KPICard
            title="Toplam Kayıt"
            value={summary?.total_records || 0}
            icon="📊"
            loading={isLoading}
            subtitle={summary?.total_records ? 'fact tablosunda' : undefined}
          />
          
          <KPICard
            title="Ortalama Oyuncu"
            value={summary?.avg_concurrent_players ? Math.round(summary.avg_concurrent_players) : 0}
            icon="👥"
            loading={isLoading}
            subtitle="eşzamanlı oyuncu"
          />
          
          <KPICard
            title="Aktif İndirim"
            value={summary?.active_discounts || 0}
            icon="🏷️"
            loading={isLoading}
            subtitle={summary?.avg_discount_pct ? `Ort. %${summary.avg_discount_pct.toFixed(1)} indirim` : undefined}
          />
        </div>

        {/* Additional KPI Cards */}
        {summary?.kpis && summary.kpis.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {summary.kpis.map((kpi: any, index: number) => (
              <KPICard
                key={index}
                title={kpi.label}
                value={kpi.value}
                icon={getIconForKPI(kpi.label)}
                loading={isLoading}
                subtitle={kpi.change_pct !== undefined ? undefined : kpi.label}
                trend={kpi.change_pct !== undefined ? {
                  value: Math.abs(kpi.change_pct),
                  isPositive: kpi.change_pct >= 0
                } : undefined}
              />
            ))}
          </div>
        )}

        {/* Latest Update Info */}
        {summary?.latest_data_date && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center">
              <span className="text-2xl mr-3">ℹ️</span>
              <div>
                <p className="text-sm font-medium text-blue-900">Son Güncelleme</p>
                <p className="text-sm text-blue-700">
                  {format(new Date(summary.latest_data_date), 'dd MMMM yyyy HH:mm')}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Welcome Message for New Users */}
        {!isLoading && summary?.total_games === 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-yellow-900 mb-2">
              👋 Hoş Geldiniz!
            </h3>
            <p className="text-yellow-800 mb-4">
              Henüz veritabanında veri yok. ETL pipeline'ını çalıştırarak veri toplamaya başlayın.
            </p>
            <div className="bg-white rounded p-4 border border-yellow-300">
              <p className="text-sm text-gray-700 font-mono">
                docker exec -it steam-backend python3 -m app.scripts.seed_initial_data
              </p>
            </div>
          </div>
        )}

        {/* Quick Stats Summary */}
        {summary && summary.total_games > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">📈 Hızlı İstatistikler</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-gray-600">İndirim Oranı</p>
                <p className="text-2xl font-bold text-gray-900">
                  {summary.active_discounts && summary.total_games 
                    ? ((summary.active_discounts / summary.total_games) * 100).toFixed(1)
                    : 0}%
                </p>
              </div>
              
              {summary.avg_discount_pct !== undefined && summary.avg_discount_pct > 0 && (
                <div>
                  <p className="text-sm text-gray-600">Ortalama İndirim</p>
                  <p className="text-2xl font-bold text-green-600">
                    %{summary.avg_discount_pct.toFixed(1)}
                  </p>
                </div>
              )}
              
              <div>
                <p className="text-sm text-gray-600">Kayıt/Oyun</p>
                <p className="text-2xl font-bold text-gray-900">
                  {summary.total_records && summary.total_games 
                    ? (summary.total_records / summary.total_games).toFixed(1)
                    : 0}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

// Helper function to get icon based on KPI label
function getIconForKPI(label: string): string {
  const lowerLabel = label.toLowerCase();
  
  if (lowerLabel.includes('oyun') || lowerLabel.includes('game')) return '🎮';
  if (lowerLabel.includes('oyuncu') || lowerLabel.includes('player')) return '👥';
  if (lowerLabel.includes('indirim') || lowerLabel.includes('discount')) return '🏷️';
  if (lowerLabel.includes('fiyat') || lowerLabel.includes('price')) return '💰';
  if (lowerLabel.includes('retention')) return '⏱️';
  if (lowerLabel.includes('churn')) return '📉';
  if (lowerLabel.includes('revenue')) return '💵';
  
  return '📊';
}
