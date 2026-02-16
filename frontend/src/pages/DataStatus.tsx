import Layout from '../components/layout/Layout';
import { useIngestionStatus } from '../hooks/useAnalytics';
import { format } from 'date-fns';

export default function DataStatus() {
  const { data: status, isLoading, error } = useIngestionStatus();

  if (error) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">
            ❌ Durum bilgisi yüklenirken bir hata oluştu.
          </p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Overall Status Card */}
        <div className={`rounded-lg shadow p-6 ${
          status?.status === 'healthy' ? 'bg-green-50' :
          status?.status === 'warning' ? 'bg-yellow-50' :
          status?.status === 'error' ? 'bg-red-50' :
          'bg-gray-50'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold mb-2">
                {status?.status === 'healthy' ? '✅ Sistem Sağlıklı' :
                 status?.status === 'warning' ? '⚠️ Dikkat Gerekiyor' :
                 status?.status === 'error' ? '❌ Hata Var' :
                 '🔄 Kontrol Ediliyor...'}
              </h2>
              <p className="text-sm text-gray-700">
                {status?.message || 'ETL pipeline durumu kontrol ediliyor...'}
              </p>
            </div>
            {status?.last_update && (
              <div className="text-right">
                <p className="text-sm text-gray-600">Son Güncelleme</p>
                <p className="text-lg font-medium">
                  {format(new Date(status.last_update), 'dd MMM yyyy HH:mm')}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Data Quality Metrics */}
        {status?.data_quality && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">📊 Veri Kalitesi Metrikleri</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Toplam Kayıt</p>
                <p className="text-3xl font-bold text-blue-900">
                  {status.data_quality.total_records?.toLocaleString() || 0}
                </p>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Geçerli Kayıt</p>
                <p className="text-3xl font-bold text-green-900">
                  {status.data_quality.valid_records?.toLocaleString() || 0}
                </p>
                {status.data_quality.total_records && status.data_quality.valid_records && (
                  <p className="text-xs text-gray-500 mt-1">
                    %{((status.data_quality.valid_records / status.data_quality.total_records) * 100).toFixed(1)}
                  </p>
                )}
              </div>

              <div className="bg-yellow-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Eksik Veri</p>
                <p className="text-3xl font-bold text-yellow-900">
                  {status.data_quality.missing_data?.toLocaleString() || 0}
                </p>
                {status.data_quality.total_records && status.data_quality.missing_data && (
                  <p className="text-xs text-gray-500 mt-1">
                    %{((status.data_quality.missing_data / status.data_quality.total_records) * 100).toFixed(1)}
                  </p>
                )}
              </div>
            </div>

            {status.data_quality.data_freshness && (
              <div className="mt-6 bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-2">Veri Tazeliği</p>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <p className="text-gray-600">Son 24 saat</p>
                    <p className="text-lg font-bold text-gray-900">
                      {status.data_quality.data_freshness.last_24h || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Son hafta</p>
                    <p className="text-lg font-bold text-gray-900">
                      {status.data_quality.data_freshness.last_week || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Son ay</p>
                    <p className="text-lg font-bold text-gray-900">
                      {status.data_quality.data_freshness.last_month || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-600">Daha eski</p>
                    <p className="text-lg font-bold text-gray-900">
                      {status.data_quality.data_freshness.older || 0}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Recent Jobs */}
        {status?.recent_jobs && status.recent_jobs.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">🔄 Son ETL İşleri</h2>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Job ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Tip
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Durum
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Başlangıç
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Süre
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {status.recent_jobs.map((job: any) => (
                    <tr key={job.job_id}>
                      <td className="px-4 py-3 text-sm font-mono text-gray-900">
                        {job.job_id.substring(0, 8)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {job.job_type}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          job.status === 'completed' ? 'bg-green-100 text-green-800' :
                          job.status === 'running' ? 'bg-blue-100 text-blue-800' :
                          job.status === 'failed' ? 'bg-red-100 text-red-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {job.status === 'completed' ? '✅ Tamamlandı' :
                           job.status === 'running' ? '🔄 Çalışıyor' :
                           job.status === 'failed' ? '❌ Başarısız' :
                           job.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {job.started_at ? format(new Date(job.started_at), 'dd MMM HH:mm') : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {job.duration ? `${job.duration}s` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Pipeline Statistics */}
        {status?.pipeline_stats && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">📈 Pipeline İstatistikleri</h2>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Toplam Çalışma</p>
                <p className="text-2xl font-bold text-gray-900">
                  {status.pipeline_stats.total_runs || 0}
                </p>
              </div>

              <div className="bg-green-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Başarılı</p>
                <p className="text-2xl font-bold text-green-900">
                  {status.pipeline_stats.successful_runs || 0}
                </p>
              </div>

              <div className="bg-red-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Başarısız</p>
                <p className="text-2xl font-bold text-red-900">
                  {status.pipeline_stats.failed_runs || 0}
                </p>
              </div>

              <div className="bg-blue-50 rounded-lg p-4">
                <p className="text-sm text-gray-600 mb-1">Başarı Oranı</p>
                <p className="text-2xl font-bold text-blue-900">
                  {status.pipeline_stats.total_runs && status.pipeline_stats.successful_runs
                    ? ((status.pipeline_stats.successful_runs / status.pipeline_stats.total_runs) * 100).toFixed(1)
                    : 0}%
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Database Tables Info */}
        {status?.database_tables && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">💾 Veritabanı Tabloları</h2>
            
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Tablo Adı
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Kayıt Sayısı
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Son Güncelleme
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {Object.entries(status.database_tables).map(([tableName, tableInfo]: [string, any]) => (
                    <tr key={tableName}>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">
                        {tableName}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {tableInfo.row_count?.toLocaleString() || 0}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {tableInfo.last_updated ? format(new Date(tableInfo.last_updated), 'dd MMM yyyy HH:mm') : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="bg-gray-50 rounded-lg shadow p-6 animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          </div>
        )}

        {/* No Data Message */}
        {!isLoading && !status && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <p className="text-yellow-800">
              ℹ️ Henüz durum bilgisi yok. ETL pipeline çalıştırılmaya başlandığında buradan izleyebilirsiniz.
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}
