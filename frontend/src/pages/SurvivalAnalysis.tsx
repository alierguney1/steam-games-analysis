import { useState } from 'react';
import Layout from '../components/layout/Layout';
import { useSurvivalAnalysis } from '../hooks/useAnalytics';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function SurvivalAnalysis() {
  const [churnThreshold, setChurnThreshold] = useState('0.5');
  const [groupBy, setGroupBy] = useState('genre_name');
  const [runAnalysis, setRunAnalysis] = useState(false);

  const { data: survivalResults, isLoading, error } = useSurvivalAnalysis(
    runAnalysis 
      ? { 
          churn_threshold_pct: parseFloat(churnThreshold),
          groupby_col: groupBy 
        }
      : undefined
  );

  const handleRunAnalysis = () => {
    setRunAnalysis(true);
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Info Card */}
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
          <h2 className="text-lg font-bold text-purple-900 mb-2">
            ℹ️ Survival (Hayatta Kalma) Analizi
          </h2>
          <p className="text-purple-800 text-sm">
            Survival analizi, oyuncuların ne kadar süre oyunda kaldığını (retention) ve 
            ne zaman oyunu bıraktığını (churn) modelleyen istatistiksel bir yöntemdir. 
            Kaplan-Meier eğrileri ve Cox PH modeli ile grup bazlı karşılaştırmalar yapılır.
          </p>
        </div>

        {/* Analysis Configuration */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">🔧 Analiz Parametreleri</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Churn Eşiği (% düşüş)
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={churnThreshold}
                onChange={(e) => setChurnThreshold(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 mt-1">
                Örn: 0.5 = oyuncu sayısı %50 düştüğünde churn
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Gruplama Kolonu
              </label>
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="genre_name">Tür (Genre)</option>
                <option value="is_free">Ücretsiz vs Ücretli</option>
                <option value="developer">Geliştirici</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={isLoading}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? '⏳ Analiz yapılıyor...' : '▶️ Analizi Çalıştır'}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">
              ❌ Analiz sırasında bir hata oluştu. Lütfen parametreleri kontrol edin.
            </p>
          </div>
        )}

        {/* Results Display */}
        {survivalResults && (
          <>
            {/* Retention Metrics */}
            {survivalResults.retention_metrics && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">📊 Retention Metrikleri</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-green-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">Retention Oranı</p>
                    <p className="text-3xl font-bold text-green-900">
                      {((survivalResults.retention_metrics.retention_rate || 0) * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Oyuncuları tutan oyunlar</p>
                  </div>

                  <div className="bg-red-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">Churn Oranı</p>
                    <p className="text-3xl font-bold text-red-900">
                      {((survivalResults.retention_metrics.churn_rate || 0) * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Oyuncu kaybeden oyunlar</p>
                  </div>

                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">Medyan Churn Süresi</p>
                    <p className="text-3xl font-bold text-blue-900">
                      {survivalResults.retention_metrics.median_time_to_churn_months || 'N/A'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">Ay cinsinden</p>
                  </div>
                </div>
              </div>
            )}

            {/* Kaplan-Meier Curves */}
            {survivalResults.kaplan_meier && survivalResults.kaplan_meier.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  📈 Kaplan-Meier Survival Eğrileri
                </h2>
                
                <p className="text-sm text-gray-600 mb-4">
                  Her eğri, belirli bir grup için zaman içinde oyuncu retention oranını gösterir.
                  Eğri ne kadar yüksekte kalırsa, o grubun retention'ı o kadar iyidir.
                </p>
                
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={prepareKMData(survivalResults.kaplan_meier)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="time" 
                      label={{ value: 'Zaman (Ay)', position: 'insideBottom', offset: -5 }}
                    />
                    <YAxis 
                      label={{ value: 'Survival Olasılığı', angle: -90, position: 'insideLeft' }}
                      domain={[0, 1]}
                    />
                    <Tooltip 
                      formatter={(value: any) => `${(value * 100).toFixed(1)}%`}
                    />
                    <Legend />
                    {getKMGroups(survivalResults.kaplan_meier).map((group, index) => (
                      <Line
                        key={group}
                        type="stepAfter"
                        dataKey={group}
                        stroke={getColorForGroup(index)}
                        name={group}
                        strokeWidth={2}
                        dot={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Cox PH Results */}
            {survivalResults.cox_ph && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">🔬 Cox Proportional Hazards Model</h2>
                
                <p className="text-sm text-gray-600 mb-4">
                  Cox PH modeli, farklı değişkenlerin churn riskine etkisini ölçer. 
                  Hazard Ratio {'>'} 1 ise risk artırır, {'<'} 1 ise azaltır.
                </p>

                {survivalResults.cox_ph.coefficients && (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Değişken
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Hazard Ratio
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            P-değeri
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                            Anlamlılık
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {Object.entries(survivalResults.cox_ph.coefficients).map(([variable, data]: [string, any]) => (
                          <tr key={variable}>
                            <td className="px-4 py-3 text-sm font-medium text-gray-900">
                              {variable}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-700">
                              {data.hazard_ratio?.toFixed(3)}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-700">
                              {data.p_value?.toFixed(4)}
                            </td>
                            <td className="px-4 py-3 text-sm">
                              {data.p_value < 0.05 ? (
                                <span className="text-green-600 font-medium">✅ Anlamlı</span>
                              ) : (
                                <span className="text-gray-500">○ Anlamsız</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {survivalResults.cox_ph.concordance && (
                  <div className="mt-4 bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">Concordance Index (C-Index)</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {survivalResults.cox_ph.concordance.toFixed(3)}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Model performansı (1.0 = mükemmel, 0.5 = rastgele)
                    </p>
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Instructions */}
        {!survivalResults && !isLoading && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-3">📝 Kullanım Talimatları</h3>
            <ol className="list-decimal list-inside space-y-2 text-gray-700">
              <li>Churn eşiğini belirleyin (örn: 0.5 = %50 oyuncu kaybı)</li>
              <li>Gruplama kolonunu seçin (tür, fiyat tipi, vb.)</li>
              <li>"Analizi Çalıştır" butonuna tıklayın</li>
              <li>Kaplan-Meier eğrilerini ve Cox PH sonuçlarını inceleyin</li>
              <li>Gruplar arası farkları retention oranları üzerinden yorumlayın</li>
            </ol>
          </div>
        )}
      </div>
    </Layout>
  );
}

// Helper functions
function prepareKMData(kmData: any[]): any[] {
  const timePoints = [...new Set(kmData.map(d => d.time))].sort((a, b) => a - b);
  const groups = [...new Set(kmData.map(d => d.group))];
  
  return timePoints.map(time => {
    const point: any = { time };
    groups.forEach(group => {
      const entry = kmData.find(d => d.time === time && d.group === group);
      point[group] = entry?.survival_probability || null;
    });
    return point;
  });
}

function getKMGroups(kmData: any[]): string[] {
  return [...new Set(kmData.map(d => d.group))];
}

function getColorForGroup(index: number): string {
  const colors = [
    '#3b82f6', // blue
    '#10b981', // green
    '#f59e0b', // amber
    '#ef4444', // red
    '#8b5cf6', // purple
    '#06b6d4', // cyan
    '#ec4899', // pink
    '#14b8a6', // teal
  ];
  return colors[index % colors.length];
}
