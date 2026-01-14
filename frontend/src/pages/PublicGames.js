import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { 
  Gamepad2, Download, Search, Filter, Star, Clock, XCircle, 
  CheckCircle, Smartphone, Globe, Apple, MessageCircle, 
  ChevronRight, Sparkles, Lock, RefreshCw
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PublicGames = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { isPortalAuthenticated } = useAuth();
  
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all'); // all, available, featured
  const [siteInfo, setSiteInfo] = useState(null);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');

  useEffect(() => {
    fetchGames();
    fetchSiteInfo();
    fetchCategories();
  }, [filter, selectedCategory]);

  const fetchGames = async () => {
    try {
      let url = `${API}/public/games?limit=100`;
      
      if (filter === 'available') {
        url += '&availability=available';
      } else if (filter === 'featured') {
        url += '&featured_only=true';
      }
      
      if (selectedCategory) {
        url += `&category=${encodeURIComponent(selectedCategory)}`;
      }
      
      const response = await axios.get(url);
      setGames(response.data);
    } catch (error) {
      console.error('Failed to fetch games:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSiteInfo = async () => {
    try {
      const response = await axios.get(`${API}/public/site-info`);
      setSiteInfo(response.data);
    } catch (error) {
      console.error('Failed to fetch site info:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await axios.get(`${API}/public/games/categories/list`);
      setCategories(response.data.categories || []);
    } catch (error) {
      console.error('Failed to fetch categories:', error);
    }
  };

  const filteredGames = games.filter(game => 
    game.name.toLowerCase().includes(search.toLowerCase()) ||
    (game.tagline && game.tagline.toLowerCase().includes(search.toLowerCase()))
  );

  const handleGetCredentials = (gameId) => {
    if (isPortalAuthenticated) {
      navigate(`/portal/credentials?game=${gameId}`);
    } else {
      navigate(`/client-login?redirect=/portal/credentials&game=${gameId}`);
    }
  };

  const handleRecharge = (gameId) => {
    if (isPortalAuthenticated) {
      navigate(`/portal/load-game?game=${gameId}`);
    } else {
      navigate(`/client-login?redirect=/portal/load-game&game=${gameId}`);
    }
  };

  const getAvailabilityIcon = (status) => {
    switch (status) {
      case 'available':
        return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      case 'maintenance':
        return <Clock className="w-4 h-4 text-yellow-400" />;
      case 'unavailable':
        return <XCircle className="w-4 h-4 text-red-400" />;
      default:
        return <CheckCircle className="w-4 h-4 text-emerald-400" />;
    }
  };

  const getAvailabilityLabel = (status) => {
    switch (status) {
      case 'available':
        return 'Available';
      case 'maintenance':
        return 'Maintenance';
      case 'unavailable':
        return 'Unavailable';
      default:
        return 'Available';
    }
  };

  const getAvailabilityColor = (status) => {
    switch (status) {
      case 'available':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'maintenance':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'unavailable':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    }
  };

  const getPlatformIcon = (platform) => {
    switch (platform) {
      case 'android':
        return <Smartphone className="w-4 h-4" />;
      case 'ios':
        return <Apple className="w-4 h-4" />;
      case 'web':
        return <Globe className="w-4 h-4" />;
      default:
        return <Smartphone className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-950 via-gray-900 to-black">
      {/* Hero Header */}
      <div className="bg-gradient-to-r from-emerald-900/30 via-purple-900/20 to-blue-900/30 border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-12 text-center">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Gamepad2 className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-3">
            Available Games
          </h1>
          <p className="text-gray-400 text-lg max-w-xl mx-auto">
            Download, explore & play your favorite games
          </p>
          <p className="text-gray-500 text-sm mt-2">
            <Lock className="w-3 h-3 inline mr-1" />
            Login required only for recharge & account access
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="sticky top-0 z-40 bg-gray-900/95 backdrop-blur-sm border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search games..."
                className="w-full pl-10 pr-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500"
                data-testid="games-search"
              />
            </div>

            {/* Filter Pills */}
            <div className="flex gap-2 overflow-x-auto pb-2 md:pb-0">
              <button
                onClick={() => setFilter('all')}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition ${
                  filter === 'all'
                    ? 'bg-emerald-500 text-white'
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                All Games
              </button>
              <button
                onClick={() => setFilter('available')}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition flex items-center gap-1 ${
                  filter === 'available'
                    ? 'bg-emerald-500 text-white'
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                <CheckCircle className="w-3 h-3" />
                Available
              </button>
              <button
                onClick={() => setFilter('featured')}
                className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition flex items-center gap-1 ${
                  filter === 'featured'
                    ? 'bg-purple-500 text-white'
                    : 'bg-gray-800 text-gray-400 hover:text-white'
                }`}
              >
                <Star className="w-3 h-3" />
                Featured
              </button>
              
              {/* Category Dropdown */}
              {categories.length > 0 && (
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="px-4 py-2 rounded-full text-sm font-medium bg-gray-800 text-gray-400 border-none focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">All Categories</option>
                  {categories.map(cat => (
                    <option key={cat} value={cat}>{cat}</option>
                  ))}
                </select>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Games Grid */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <RefreshCw className="w-8 h-8 text-emerald-500 animate-spin" />
          </div>
        ) : filteredGames.length === 0 ? (
          <div className="text-center py-20">
            <Gamepad2 className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No games found</h3>
            <p className="text-gray-400">Try adjusting your search or filters</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredGames.map(game => (
              <GameCard 
                key={game.id} 
                game={game}
                onGetCredentials={handleGetCredentials}
                onRecharge={handleRecharge}
                getAvailabilityIcon={getAvailabilityIcon}
                getAvailabilityLabel={getAvailabilityLabel}
                getAvailabilityColor={getAvailabilityColor}
                getPlatformIcon={getPlatformIcon}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-12">
        <div className="max-w-6xl mx-auto px-4 py-12">
          <div className="text-center">
            <h3 className="text-xl font-semibold text-white mb-2">Need help?</h3>
            <p className="text-gray-400 mb-6">{siteInfo?.support_text || 'Chat with us on Facebook!'}</p>
            
            <div className="flex justify-center gap-4">
              {siteInfo?.contact?.facebook && (
                <a
                  href={siteInfo.contact.facebook}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition font-medium"
                  data-testid="footer-facebook"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                  </svg>
                  Facebook Page
                </a>
              )}
              
              {siteInfo?.contact?.messenger && (
                <a
                  href={siteInfo.contact.messenger}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl transition font-medium"
                  data-testid="footer-messenger"
                >
                  <MessageCircle className="w-5 h-5" />
                  Chat on Messenger
                </a>
              )}
            </div>

            <p className="text-gray-600 text-sm mt-8">
              © 2024 {siteInfo?.name || 'VaultLink'}. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

// Game Card Component
const GameCard = ({ 
  game, 
  onGetCredentials, 
  onRecharge,
  getAvailabilityIcon,
  getAvailabilityLabel,
  getAvailabilityColor,
  getPlatformIcon
}) => {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden hover:border-gray-700 transition group" data-testid={`game-card-${game.id}`}>
      {/* Game Image/Icon */}
      <div className="relative h-40 bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center">
        {game.thumbnail || game.icon_url ? (
          <img 
            src={game.thumbnail || game.icon_url} 
            alt={game.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <Gamepad2 className="w-16 h-16 text-gray-700" />
        )}
        
        {/* Featured Badge */}
        {game.is_featured && (
          <div className="absolute top-3 left-3 flex items-center gap-1 px-2 py-1 bg-purple-500/90 text-white text-xs font-medium rounded-full">
            <Sparkles className="w-3 h-3" />
            Featured
          </div>
        )}
        
        {/* Availability Badge */}
        <div className={`absolute top-3 right-3 flex items-center gap-1 px-2 py-1 border rounded-full text-xs font-medium ${getAvailabilityColor(game.availability_status)}`}>
          {getAvailabilityIcon(game.availability_status)}
          {getAvailabilityLabel(game.availability_status)}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="text-lg font-bold text-white mb-1">{game.name}</h3>
        {game.tagline && (
          <p className="text-gray-400 text-sm mb-3">{game.tagline}</p>
        )}
        
        {/* Platforms */}
        {game.platforms && game.platforms.length > 0 && (
          <div className="flex items-center gap-2 mb-4">
            {game.platforms.map(platform => (
              <span key={platform} className="flex items-center gap-1 text-gray-500 text-xs">
                {getPlatformIcon(platform)}
                {platform.charAt(0).toUpperCase() + platform.slice(1)}
              </span>
            ))}
          </div>
        )}

        {/* Download Button - Always visible */}
        {game.download_url && (
          <a
            href={game.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full mb-3 flex items-center justify-center gap-2 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold rounded-xl transition"
            data-testid={`download-btn-${game.id}`}
          >
            <Download className="w-4 h-4" />
            Download
          </a>
        )}

        {/* Action Buttons - Require Login */}
        <div className="flex gap-2">
          <button
            onClick={() => onGetCredentials(game.id)}
            className="flex-1 flex items-center justify-center gap-1 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg transition"
            data-testid={`get-id-btn-${game.id}`}
          >
            <Lock className="w-3 h-3" />
            Get ID/PW
          </button>
          <button
            onClick={() => onRecharge(game.id)}
            className="flex-1 flex items-center justify-center gap-1 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg transition"
            data-testid={`recharge-btn-${game.id}`}
          >
            <ChevronRight className="w-3 h-3" />
            Recharge
          </button>
        </div>
      </div>
    </div>
  );
};

export default PublicGames;
