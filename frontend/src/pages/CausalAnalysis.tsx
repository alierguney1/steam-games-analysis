import { useState } from 'react';
import Layout from '../components/layout/Layout';
import { useDiDAnalysis } from '../hooks/useAnalytics';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

export default function CausalAnalysis() {
  const [treatmentGameId, setTreatmentGameId] = useState('');
  const [controlGameId, setControlGameId] = useState('');
  const [runAnalysis, setRunAnalysis] = useState(false);

  const { data: didResults, isLoading, error } = useDiDAnalysis(
    runAnalysis && treatmentGameId && controlGameId 
      ? { treatment_game_id: treatmentGameId, control_game_id: controlGameId }
      : undefined
  );

  const handleRunAnalysis = () => {
    if (treatmentGameId && controlGameId) {
      setRunAnalysis(true);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Info Card */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h2 className="text-lg font-bold text-blue-900 mb-2">
            ℹ️ Nedensel Analiz (Difference-in-Differences)
          </h2>
          <p className="text-blue-800 text-sm">
            DiD modeli, fiyat değişikliklerinin oyuncu sayısına <strong>nedensel etkisini</strong> ölçer. 
            İndirim yapan bir oyunu (treatment) indirim yapmayan benzer bir oyunla (control) karşılaştırarak 
            gerçek etkiyi izole eder.
          </p>
        </div>

        {/* Analysis Configuration */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">🔧 Analiz Parametreleri</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Treatment Oyun ID (İndirim yapan)
              </label>
              <input
                type="text"
                value={treatmentGameId}
                onChange={(e) => setTreatmentGameId(e.target.value)}
                placeholder="Örn: 730 (CS:GO)"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Control Oyun ID (İndirim yapmayan)
              </label>
              <input
                type="text"
                value={controlGameId}
                onChange={(e) => setControlGameId(e.target.value)}
                placeholder="Örn: 570 (Dota 2)"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={!treatmentGameId || !controlGameId || isLoading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? '⏳ Analiz yapılıyor...' : '▶️ Analizi Çalıştır'}
          </button>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800">
              ❌ Analiz sırasında bir hata oluştu. Lütfen oyun ID'lerini kontrol edin.
            </p>
          </div>
        )}

        {/* Results Display */}
        {didResults && (
          <>
            {/* Main Estimation Results */}
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">📊 DiD Tahmin Sonuçları</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-blue-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-1">ATT (Average Treatment Effect on Treated)</p>
                  <p className="text-3xl font-bold text-blue-900">
                    {didResults.main_estimation?.att?.toFixed(2) || 'N/A'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">İndirimin oyuncu sayısına etkisi</p>
                </div>

                <div className={`rounded-lg p-4 ${
                  didResults.main_estimation?.p_value < 0.05 ? 'bg-green-50' : 'bg-yellow-50'
                }`}>
                  <p className="text-sm text-gray-600 mb-1">P-değeri</p>
                  <p className={`text-3xl font-bold ${
                    didResults.main_estimation?.p_value < 0.05 ? 'text-green-900' : 'text-yellow-900'
                  }`}>
                    {didResults.main_estimation?.p_value?.toFixed(4) || 'N/A'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {didResults.main_estimation?.p_value < 0.05 
                      ? '✅ İstatistiksel olarak anlamlı' 
                      : '⚠️ İstatistiksel olarak anlamsız'}
                  </p>
                </div>

                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-1">Standart Hata</p>
                  <p className="text-3xl font-bold text-gray-900">
                    {didResults.main_estimation?.std_error?.toFixed(2) || 'N/A'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Tahmin hassasiyeti</p>
                </div>
              </div>

              {didResults.main_estimation?.confidence_interval && (
                <div className="mt-4 bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-2">%95 Güven Aralığı</p>
                  <p className="text-lg font-medium text-gray-900">
                    [{didResults.main_estimation.confidence_interval[0]?.toFixed(2)}, {' '}
                    {didResults.main_estimation.confidence_interval[1]?.toFixed(2)}]
                  </p>
                </div>
              )}
            </div>

            {/* Parallel Trends Test */}
            {didResults.parallel_trends && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">📈 Paralel Trend Testi</h2>
                
                <div className={`rounded-lg p-4 ${
                  didResults.parallel_trends.parallel_trends_valid ? 'bg-green-50' : 'bg-red-50'
                }`}>
                  <p className="text-lg font-bold mb-2 ${
                    didResults.parallel_trends.parallel_trends_valid ? 'text-green-900' : 'text-red-900'
                  }">
                    {didResults.parallel_trends.parallel_trends_valid 
                      ? '✅ Paralel trend varsayımı geçerli' 
                      : '❌ Paralel trend varsayımı ihlal edildi'}
                  </p>
                  <p className="text-sm text-gray-700">
                    P-değeri: {didResults.parallel_trends.trend_test_p_value?.toFixed(4) || 'N/A'}
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Paralel trend, DiD modelinin temel varsayımıdır. Treatment öncesi dönemde 
                    treatment ve control gruplarının benzer trendler göstermesi gerekir.
                  </p>
                </div>
              </div>
            )}

            {/* Visualization */}
            {didResults.visualization_data && didResults.visualization_data.length > 0 && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">
                  📉 Treatment vs Control Karşılaştırması
                </h2>
                
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={didResults.visualization_data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="period" />
                    <YAxis label={{ value: 'Ortalama Oyuncu', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <ReferenceLine 
                      x={didResults.treatment_start_period} 
                      stroke="#ef4444" 
                      strokeDasharray="5 5"
                      label="Treatment Başlangıcı"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="treatment_group" 
                      stroke="#3b82f6" 
                      name="Treatment Group"
                      strokeWidth={2}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="control_group" 
                      stroke="#10b981" 
                      name="Control Group"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Placebo Test Results */}
            {didResults.placebo_test && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">🧪 Placebo Testi</h2>
                
                <p className="text-sm text-gray-600 mb-4">
                  Placebo testi, treatment öncesi dönemde sahte bir treatment ataması yaparak 
                  modelin güvenilirliğini test eder.
                </p>

                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-600 mb-1">Placebo ATT</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {didResults.placebo_test.placebo_att?.toFixed(2) || 'N/A'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {Math.abs(didResults.placebo_test.placebo_att || 0) < Math.abs(didResults.main_estimation?.att || 0) / 2
                      ? '✅ Placebo etkisi beklenen seviyede' 
                      : '⚠️ Placebo etkisi yüksek - dikkatli yorumlanmalı'}
                  </p>
                </div>
              </div>
            )}
          </>
        )}

        {/* Instructions */}
        {!didResults && !isLoading && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
            <h3 className="text-lg font-bold text-gray-900 mb-3">📝 Kullanım Talimatları</h3>
            <ol className="list-decimal list-inside space-y-2 text-gray-700">
              <li>Yukarıdaki formu kullanarak bir treatment ve control oyun ID'si girin</li>
              <li>Treatment oyunu: İndirim yapan veya fiyat değişikliği olan oyun</li>
              <li>Control oyunu: Benzer özelliklere sahip ama fiyat değişikliği olmayan oyun</li>
              <li>"Analizi Çalıştır" butonuna tıklayın</li>
              <li>Sonuçları ATT, p-değeri ve paralel trend testleri üzerinden yorumlayın</li>
            </ol>
          </div>
        )}
      </div>
    </Layout>
  );
}
