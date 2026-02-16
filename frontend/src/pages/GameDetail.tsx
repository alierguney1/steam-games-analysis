import { useParams } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { useGame } from '../hooks/useAnalytics';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

export default function GameDetail() {
  const { id } = useParams<{ id: string }>();
  const gameId = id ? parseInt(id, 10) : 0;
  
  const { data: game, isLoading, error } = useGame(gameId);

  if (error) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">❌ Oyun yüklenirken bir hata oluştu.</p>
        </div>
      </Layout>
    );
  }

  if (isLoading) {
    return (
      <Layout>
        <div className="space-y-6 animate-pulse">
          <div className="h-32 bg-gray-200 rounded-lg"></div>
          <div className="h-96 bg-gray-200 rounded-lg"></div>
        </div>
      </Layout>
    );
  }

  if (!game) {
    return (
      <Layout>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">⚠️ Oyun bulunamadı.</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title={game.name} description="Oyun detayları ve trend analizleri">
      <div className="space-y-6">
        {/* Game Info Card */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">{game.name}</h2>
              
              <div className="space-y-2 text-gray-700">
                {game.developer && (
                  <p>
                    <span className="font-medium">Geliştirici:</span> {game.developer}
                  </p>
                )}
                
                {game.publisher && (
                  <p>
                    <span className="font-medium">Yayıncı:</span> {game.publisher}
                  </p>
                )}
                
                {game.release_date && (
                  <p>
                    <span className="font-medium">Çıkış Tarihi:</span>{' '}
                    {new Date(game.release_date).toLocaleDateString('tr-TR')}
                  </p>
                )}
                
                {game.appid && (
                  <p>
                    <span className="font-medium">Steam App ID:</span> {game.appid}
                  </p>
                )}
              </div>

              {game.is_free && (
                <div className="mt-4">
                  <span className="inline-block bg-green-100 text-green-800 px-3 py-1 rounded-lg font-medium">
                    ✅ ÜCRETSİZ OYUN
                  </span>
                </div>
              )}
            </div>

            <div className="space-y-4">
              {/* Reviews */}
              {game.positive_reviews !== undefined && game.negative_reviews !== undefined && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-600 mb-2">İncelemeler</h3>
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <p className="text-green-600 font-bold text-xl">
                        👍 {game.positive_reviews.toLocaleString()}
                      </p>
                      <p className="text-sm text-gray-500">Olumlu</p>
                    </div>
                    <div className="flex-1">
                      <p className="text-red-600 font-bold text-xl">
                        👎 {game.negative_reviews.toLocaleString()}
                      </p>
                      <p className="text-sm text-gray-500">Olumsuz</p>
                    </div>
                  </div>
                  <div className="mt-2">
                    <p className="text-sm text-gray-600">
                      Onay oranı:{' '}
                      <span className="font-bold">
                        {((game.positive_reviews / (game.positive_reviews + game.negative_reviews)) * 100).toFixed(1)}%
                      </span>
                    </p>
                  </div>
                </div>
              )}

              {/* Owner Estimation (from SteamSpy) */}
              {game.steamspy_owners_min !== undefined && game.steamspy_owners_max !== undefined && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="text-sm font-medium text-gray-600 mb-2">Tahmini Sahip Sayısı</h3>
                  <p className="text-2xl font-bold text-gray-900">
                    {game.steamspy_owners_min.toLocaleString()} - {game.steamspy_owners_max.toLocaleString()}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">SteamSpy tahmini</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Player Trends Chart */}
        {game.player_history && game.player_history.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">📊 Oyuncu Trendi</h2>
            
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={game.player_history}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(date) => format(new Date(date), 'MMM yyyy')}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(date) => format(new Date(date), 'dd MMM yyyy')}
                  formatter={(value: any) => [value?.toLocaleString(), 'Oyuncular']}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="avg_players" 
                  stroke="#3b82f6" 
                  name="Ortalama Oyuncu"
                  strokeWidth={2}
                />
                <Line 
                  type="monotone" 
                  dataKey="peak_players" 
                  stroke="#10b981" 
                  name="Pik Oyuncu"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Price History Chart */}
        {game.price_history && game.price_history.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">💰 Fiyat Geçmişi</h2>
            
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={game.price_history}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(date) => format(new Date(date), 'MMM yyyy')}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(date) => format(new Date(date), 'dd MMM yyyy')}
                  formatter={(value: any) => [`$${value}`, 'Fiyat']}
                />
                <Legend />
                <Line 
                  type="stepAfter" 
                  dataKey="current_price" 
                  stroke="#8b5cf6" 
                  name="Güncel Fiyat"
                  strokeWidth={2}
                />
                {game.price_history.some((p: any) => p.discount_pct > 0) && (
                  <Line 
                    type="stepAfter" 
                    dataKey="discount_pct" 
                    stroke="#ef4444" 
                    name="İndirim %"
                    strokeWidth={2}
                    yAxisId="right"
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* No Data Message */}
        {(!game.player_history || game.player_history.length === 0) && 
         (!game.price_history || game.price_history.length === 0) && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
            <p className="text-yellow-800">
              ℹ️ Bu oyun için henüz tarihsel veri yok. ETL pipeline'ı düzenli çalıştırıldıkça veriler toplanacaktır.
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}
