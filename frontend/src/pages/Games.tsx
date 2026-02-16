import { useState } from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { useGames } from '../hooks/useAnalytics';

export default function Games() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const perPage = 20;

  const { data: gamesData, isLoading, error } = useGames({
    limit: perPage,
    offset: (page - 1) * perPage,
    search: search || undefined,
  });

  if (error) {
    return (
      <Layout>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">
            ❌ Oyunlar yüklenirken bir hata oluştu.
          </p>
        </div>
      </Layout>
    );
  }

  const games = gamesData?.items || [];
  const total = gamesData?.total || 0;
  const totalPages = Math.ceil(total / perPage);

  return (
    <Layout>
      <div className="space-y-6">
        {/* Search Bar */}
        <div className="bg-white rounded-lg shadow p-4">
          <input
            type="text"
            placeholder="🔍 Oyun ara..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Games List */}
        {isLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
                <div className="h-6 bg-gray-200 rounded w-1/2 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : games.length === 0 ? (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
            <p className="text-yellow-800 text-lg">
              {search ? '🔍 Arama sonucu bulunamadı.' : '📦 Henüz oyun yok.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {games.map((game: any) => (
              <div key={game.game_id} className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-xl font-bold text-gray-900 mb-2">
                      {game.name}
                    </h3>
                    
                    <div className="space-y-1 text-sm text-gray-600">
                      {game.developer && (
                        <p>
                          <span className="font-medium">Geliştirici:</span> {game.developer}
                        </p>
                      )}
                      
                      {game.release_date && (
                        <p>
                          <span className="font-medium">Çıkış:</span>{' '}
                          {new Date(game.release_date).toLocaleDateString('tr-TR')}
                        </p>
                      )}
                      
                      {game.positive_reviews !== undefined && game.negative_reviews !== undefined && (
                        <p>
                          <span className="font-medium">İncelemeler:</span>{' '}
                          <span className="text-green-600">👍 {game.positive_reviews}</span>
                          {' / '}
                          <span className="text-red-600">👎 {game.negative_reviews}</span>
                        </p>
                      )}
                    </div>

                    {game.is_free && (
                      <span className="inline-block mt-2 bg-green-100 text-green-800 text-xs px-2 py-1 rounded">
                        ÜCRETSİZ
                      </span>
                    )}
                  </div>

                  <div className="ml-4">
                    <Link
                      to={`/games/${game.game_id}`}
                      className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      Detaylar →
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-600">
                {total} oyundan {(page - 1) * perPage + 1}-{Math.min(page * perPage, total)} arası gösteriliyor
              </p>
              
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  ← Önceki
                </button>
                
                <span className="px-4 py-2 bg-blue-600 text-white rounded-lg">
                  {page} / {totalPages}
                </span>
                
                <button
                  onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Sonraki →
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
